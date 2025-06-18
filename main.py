import os
import logging
from config import settings
from core.data_loader import load_text_file, load_pdf_file, load_all_texts_from_dir, split_pdf_to_chunks
from core.extractor import KnowledgeExtractor
from core.standardizer import Standardizer
from database.graph_builder import GraphBuilder
from utils.utils import load_json, setup_logger

def main():
    """
    Orchestrates the entire knowledge graph construction pipeline.
    """
    setup_logger()

    try:
        logging.info("Starting the knowledge graph construction pipeline...")

        # --- 1. Load Configuration and Data ---
        logging.info("Loading configurations and data...")
        ontology = load_json('config/ontology.json')
        if not ontology:
            logging.error("Failed to load ontology.json. Exiting.")
            return

        data_dir = 'data'
        all_texts = load_all_texts_from_dir(data_dir)
        if not all_texts:
            logging.error(f"No valid txt or pdf files found in {data_dir}. Exiting.")
            return

        # --- 2. Instantiate Core Components ---
        logging.info("Initializing core components...")
        extractor = KnowledgeExtractor(api_key=settings.OPENROUTER_API_KEY)
        standardizer = Standardizer(ontology)
        graph_builder = GraphBuilder(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )

        for fname, document_text in all_texts:
            logging.info(f"\n===== Processing file: {fname} =====")
            if not document_text or not document_text.strip():
                logging.warning(f"File {fname} is empty or could not extract any text. Skipping.")
                continue

            # 针对PDF分块处理
            is_pdf = fname.lower().endswith('.pdf')
            all_entities, all_triples = [], []
            if is_pdf:
                pdf_path = os.path.join(data_dir, fname)
                # 估算LLM最大字符数，保守按max_tokens*4
                max_chunk_chars = settings.LLM_MAX_TOKENS * 4
                chunks = split_pdf_to_chunks(pdf_path, max_chunk_chars)
                logging.info(f"PDF will be split into {len(chunks)} chunks for extraction.")
                for i, chunk in enumerate(chunks):
                    logging.info(f"Extracting chunk {i+1}/{len(chunks)}...")
                    entities, triples = extractor.extract(chunk, ontology)
                    all_entities.extend(entities)
                    all_triples.extend(triples)
            else:
                entities, triples = extractor.extract(document_text, ontology)
                all_entities.extend(entities)
                all_triples.extend(triples)

            if not all_triples:
                logging.warning("Extractor returned no triples. Skipping this file.")
                continue
            logging.info(f"Extracted {len(all_entities)} entities and {len(all_triples)} raw triples.")

            # --- 4. Standardize the Extracted Knowledge ---
            logging.info("Step 2: Standardizing extracted triples...")
            standardized_triples = standardizer.standardize(all_entities, all_triples)
            logging.info(f"Obtained {len(standardized_triples)} standardized triples.")

            # --- 5. Build the Knowledge Graph ---
            logging.info("Step 3: Building the knowledge graph in Neo4j...")
            logging.info("Clearing existing data from the database...")
            graph_builder.clear_database()
            logging.info("Writing new data to the database...")
            graph_builder.build_graph(standardized_triples)
            logging.info("Knowledge graph construction complete for this file.")

    except Exception as e:
        logging.error(f"An unexpected error occurred in the main pipeline: {e}", exc_info=True)
    finally:
        if 'graph_builder' in locals() and graph_builder:
            graph_builder.close()
            logging.info("Neo4j connection closed.")


if __name__ == "__main__":
    main()
