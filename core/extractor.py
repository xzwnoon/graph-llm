import json
import logging
from openai import OpenAI, APIError
from config import settings

class KnowledgeExtractor:
    """
    Extracts entities and relationships from text using an LLM.
    """
    def __init__(self, api_key: str = None):
        """
        Initializes the extractor with an API key and sets up the LLM client.
        """
        self.client = OpenAI(
            base_url=settings.LLM_API_BASE,
            api_key=api_key or settings.OPENROUTER_API_KEY,
            timeout=settings.LLM_TIMEOUT
        )
        self.model = settings.LLM_MODEL_NAME
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE

    def _call_llm(self, system_prompt: str, user_prompt: str) -> dict | None:
        """
        Makes a call to the LLM API and returns the parsed JSON response.
        Includes robust error handling for API-specific issues.
        """
        raw_content = None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=settings.LLM_TIMEOUT
            )
            raw_content = response.choices[0].message.content
            return json.loads(raw_content)
        except APIError as e:
            logging.error(f"LLM API returned an error: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from LLM response: {e}")
            if raw_content:
                logging.debug(f"LLM raw response content that failed to parse: {raw_content}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during the LLM call: {e}", exc_info=True)
            return None

    def _get_entity_extraction_prompt(self, text: str, ontology: dict) -> tuple[str, str]:
        """
        Creates the system and user prompts for the entity extraction phase.
        """
        system_prompt = "You are a materials science expert. Your task is to extract named entities from a given text based on a predefined list of entity types. Your output must be a JSON object with a single key 'entities' containing a list of objects."
        
        user_prompt_template = """
From the TEXT below, identify and extract all entities matching the following types: {entity_types}.

**Entity Types and Descriptions:**
- `AluminumAlloy`: A specific aluminum alloy, e.g., '7075-T6', 'Al-Si alloy'.
- `AlloyingElement`: An element added to aluminum, e.g., 'Cu', 'Magnesium'.
- `ProcessingTechnique`: A manufacturing or treatment process, e.g., 'Cryorolling', 'T6 Aging'.
- `MechanicalProperty`: A measure of material performance, e.g., 'Hardness', 'Tensile Strength'.
- `Microstructure`: A microscopic feature of the material, e.g., 'Precipitate', 'Grain Size'.

**Output Format:**
- Provide the output as a JSON object.
- The object must have a single key "entities" which is an array of objects.
- Each object in the array must have two keys: 'name' (the extracted entity text) and 'type' (one of the predefined entity types).
- Do not extract general terms; only specific instances.

---
**TEXT:**
'''
{text}
'''
"""
        entity_types_str = ", ".join(ontology.get("node_labels", []))
        user_prompt = user_prompt_template.format(entity_types=entity_types_str, text=text)
        return system_prompt, user_prompt

    def _get_relation_extraction_prompt(self, text: str, entities: list, ontology: dict) -> tuple[str, str]:
        """
        Creates the system and user prompts for the relation extraction phase.
        优化prompt，要求输出更细致的关系和影响描述。
        """
        system_prompt = (
            "You are a materials science expert specializing in aluminum alloys, tasked with building a knowledge graph. "
            "Your goal is to extract factual and specific relationships from a given text based on a predefined ontology. "
            "For any 'affect' or 'influence' relationship, please specify the direction and nature of the effect, such as 'increase', 'decrease', 'enhance', 'reduce', 'no effect', etc. "
            "Use the most specific relation type possible from the ontology. If the effect is described in natural language (e.g., '提升', '增强', '降低', '无影响'), map it to the closest ontology relation type. "
            "The output must be a JSON object with a key 'triples'."
        )
        user_prompt_template = """
从下述TEXT和ENTITY_LIST中，抽取所有实体之间的具体影响关系。对于“影响”类关系，请细化为“提升”、“降低”、“增强”、“减弱”、“无影响”等，并明确指出影响的对象和方向。

**Ontology Constraints:**
- 关系类型必须为以下之一：{relation_types}
- 若原文为自然语言描述（如“提升”、“增强”），请尽量映射为本体中的标准关系类型。

**输出格式示例：**
{{
  "triples": [
    {{"subject": "单级时效", "relation": "INCREASES_PROPERTY", "object": "强度"}},
    {{"subject": "双级时效", "relation": "DECREASES_PROPERTY", "object": "电导率"}},
    {{"subject": "T6处理", "relation": "NO_EFFECT_ON", "object": "延展性"}}
  ]
}}

---
**ENTITY_LIST:**
{entities}

**TEXT:**
'''
{text}
'''
"""
        relation_types_str = ", ".join(ontology.get("relationship_types", []))
        entities_str = json.dumps(entities, indent=2, ensure_ascii=False)
        user_prompt = user_prompt_template.format(
            relation_types=relation_types_str,
            entities=entities_str,
            text=text
        )
        return system_prompt, user_prompt

    def extract(self, text: str, ontology: dict) -> tuple[list, list]:
        """
        Performs the two-phase extraction process.
        """
        # Phase 1: Entity Extraction
        logging.info("Starting Phase 1: Entity Extraction")
        ent_system_prompt, ent_user_prompt = self._get_entity_extraction_prompt(text, ontology)
        entity_data = self._call_llm(ent_system_prompt, ent_user_prompt)
        
        if not entity_data or "entities" not in entity_data or not isinstance(entity_data["entities"], list):
            logging.error("Entity extraction failed or returned invalid format.")
            return [], []
        
        entities = entity_data["entities"]
        logging.info(f"Phase 1 complete. Found {len(entities)} entities.")

        # Phase 2: Relation Extraction
        if not entities:
            logging.warning("No entities found, skipping relation extraction.")
            return [], []

        logging.info("Starting Phase 2: Relation Extraction")
        rel_system_prompt, rel_user_prompt = self._get_relation_extraction_prompt(text, entities, ontology)
        relation_data = self._call_llm(rel_system_prompt, rel_user_prompt)

        if not relation_data or "triples" not in relation_data or not isinstance(relation_data["triples"], list):
            logging.error("Relation extraction failed or returned invalid format.")
            return entities, []
        
        triples = relation_data["triples"]
        logging.info(f"Phase 2 complete. Found {len(triples)} relations.")
        
        return entities, triples
