import logging

# 关系标准化映射
RELATION_STANDARD_MAP = {
    "提升": "INCREASES_PROPERTY",
    "增强": "INCREASES_PROPERTY",
    "increase": "INCREASES_PROPERTY",
    "improve": "INCREASES_PROPERTY",
    "improves": "INCREASES_PROPERTY",
    "enhance": "INCREASES_PROPERTY",
    "enhances": "INCREASES_PROPERTY",
    "降低": "DECREASES_PROPERTY",
    "减弱": "DECREASES_PROPERTY",
    "decrease": "DECREASES_PROPERTY",
    "reduce": "DECREASES_PROPERTY",
    "reduces": "DECREASES_PROPERTY",
    "diminish": "DECREASES_PROPERTY",
    "diminishes": "DECREASES_PROPERTY",
    "无影响": "NO_EFFECT_ON",
    "no effect": "NO_EFFECT_ON",
    "not affect": "NO_EFFECT_ON",
    "does not affect": "NO_EFFECT_ON"
}

class Standardizer:
    """
    Normalizes entities in extracted triples against a canonical ontology map.
    """
    def __init__(self, ontology: dict):
        """
        Initializes the standardizer with the ontology.
        """
        self.ontology = ontology
        self.standardization_map = self._create_reverse_map()

    def _create_reverse_map(self) -> dict:
        """
        Creates a reverse mapping from synonym to standard name.
        """
        reverse_map = {}
        for standard_name, synonyms in self.ontology.get("standardization_map", {}).items():
            for synonym in synonyms:
                reverse_map[synonym.lower()] = standard_name
        return reverse_map

    def get_standard_name(self, name: str) -> str:
        """
        Gets the standard name for a given entity name.
        """
        return self.standardization_map.get(name.lower(), name)

    def standardize_relation(self, relation: str) -> str:
        """
        标准化关系类型，将自然语言关系归一化为本体标准类型。
        """
        r = relation.lower().strip()
        return RELATION_STANDARD_MAP.get(r, relation)

    def standardize(self, entities: list[dict], triples: list[dict]) -> list[dict]:
        """
        Standardizes the subject and object of each triple.

        Args:
            entities: A list of extracted entities with their types.
            triples: A list of raw SPO triples.

        Returns:
            A list of standardized triples with entity types included.
        """
        standardized_triples = []
        
        entity_type_map = {self.get_standard_name(e['name']): e['type'] for e in entities}
        entity_name_map = {e['name']: self.get_standard_name(e['name']) for e in entities}

        for triple in triples:
            subject_original = triple.get("subject")
            object_original = triple.get("object")
            relation = triple.get("relation")

            if not all([subject_original, object_original, relation]):
                logging.warning(f"Skipping malformed triple: {triple}")
                continue
            
            subject_std = entity_name_map.get(subject_original, self.get_standard_name(subject_original))
            object_std = entity_name_map.get(object_original, self.get_standard_name(object_original))

            subject_type = entity_type_map.get(subject_std)
            object_type = entity_type_map.get(object_std)
            
            if not subject_type or not object_type:
                logging.warning(f"Could not determine type for triple: ({subject_std}, {object_std}). Skipping.")
                continue

            relation_std = self.standardize_relation(relation)

            standardized_triples.append({
                "subject": {"name": subject_std, "type": subject_type},
                "object": {"name": object_std, "type": object_type},
                "relation": relation_std
            })
        
        return standardized_triples
