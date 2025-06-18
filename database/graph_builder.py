import logging
from neo4j import GraphDatabase, exceptions

class GraphBuilder:
    """
    Handles all interactions with the Neo4j database.
    """
    def __init__(self, uri, user, password):
        """
        Initializes the database driver.
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logging.info("Successfully connected to Neo4j database.")
        except exceptions.AuthError as e:
            logging.error(f"Neo4j authentication failed: {e}")
            self.driver = None
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        """
        Closes the database connection.
        """
        if self.driver:
            self.driver.close()

    def _execute_query(self, query, parameters=None):
        """
        Executes a Cypher query in a transaction.
        """
        if not self.driver:
            logging.error("No database connection. Cannot execute query.")
            return
            
        with self.driver.session() as session:
            try:
                session.run(query, parameters)
            except Exception as e:
                logging.error(f"Failed to execute query '{query[:50]}...': {e}")


    def clear_database(self):
        """
        Deletes all nodes and relationships from the graph.
        """
        logging.warning("Clearing all data from the Neo4j database.")
        query = "MATCH (n) DETACH DELETE n"
        self._execute_query(query)

    def build_graph(self, triples: list[dict]):
        """
        Builds the graph by creating nodes and relationships from standardized triples
        using an efficient, single-batch transaction.
        """
        if not self.driver:
            logging.error("Cannot build graph due to connection failure.")
            return
        if not triples:
            logging.warning("No triples provided to build the graph. Skipping database operation.")
            return

        logging.info(f"Starting batch import of {len(triples)} triples into Neo4j...")
        with self.driver.session() as session:
            try:
                session.execute_write(self._create_graph_from_triples, triples)
                logging.info(f"Successfully completed batch import of {len(triples)} triples.")
            except exceptions.ClientError as e:
                if "apoc.merge" in e.message:
                    logging.error(
                        "A Neo4j error occurred, possibly because the APOC library is not installed. "
                        "The query requires `apoc.merge.node` and `apoc.merge.relationship`. "
                        f"Details: {e}"
                    )
                else:
                    logging.error(f"Failed to write batch to database due to a client error: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred during batch graph build: {e}", exc_info=True)


    @staticmethod
    def _create_graph_from_triples(tx, triples: list[dict]):
        """
        A static method that executes the batch-creation Cypher query within a transaction.
        This uses APOC procedures for safely handling dynamic labels and relationship types.
        """
        query = """
        UNWIND $triples as triple
        CALL apoc.merge.node([triple.subject.type], {name: triple.subject.name}) YIELD node as a
        CALL apoc.merge.node([triple.object.type], {name: triple.object.name}) YIELD node as b
        CALL apoc.merge.relationship(a, triple.relation, {}, {}, b) YIELD rel
        RETURN count(a) as nodes_processed
        """
        tx.run(query, triples=triples)
