import requests
from urllib.parse import urljoin
import logging
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError

logger = logging.getLogger("console")


class SolrAPIError(Exception):
    """Base exception for SolrAPI errors"""
    pass


def get_target_for_collection_alias(base_url, collection_alias):
    url = urljoin(base_url, "api/aliases")
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        aliases = resp.json().get("aliases", [])
        if collection_alias in aliases:
            return aliases[collection_alias]
        else:
            return None
    except (RequestException, JSONDecodeError) as e:
        return None


class SolrManagementAPI:
    def __init__(self, base_url, collection, logging_verbose=0):
        self.base_url = base_url
        self.collection = collection
        self.logging_verbose = logging_verbose
        self.request_timeout = 10

    def _handle_request_exception(self, e, operation):
        """Handle request exceptions and convert to SolrAPIError"""
        raise SolrAPIError(f"Error while {operation}: {str(e)}") from e

    def get_collection_schema(self):
        url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        try:
            res = requests.get(url, timeout=self.request_timeout)
            res.raise_for_status()
            return res.json()
        except (RequestException, JSONDecodeError) as e:
            self._handle_request_exception(e, "getting collection schema")

    def check_collection_has_field(self, field):
        schema = self.get_collection_schema()
        fields = schema['schema']['fields']
        for f in fields:
            if f['name'] == field:
                return True
        return False

    def get_field_types(self):
        schema = self.get_collection_schema()
        return schema["schema"]["fieldTypes"]

    def _make_post(self, url, data):
        try:
            resp = requests.post(url, json=data, timeout=self.request_timeout)
            resp.raise_for_status()
            return resp.json()
        except (RequestException, JSONDecodeError) as e:
            self._handle_request_exception(e, "making POST request")

    def add_field_types(self, field_types, bulk=True):
        schema_url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        if bulk:
            request = {"add-field-type": field_types}
            if self.logging_verbose >= 2:
                logger.info(f"Bulk creating field types {field_types}")
            self._make_post(schema_url, request)
        else:
            for field_type in field_types:
                request = {"add-field-type": field_type}
                if self.logging_verbose >= 2:
                    logger.info(f"Creating field type {field_type['name']}")
                self._make_post(schema_url, request)

    def add_fields(self, fields, bulk=True):
        schema_url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        if bulk:
            request = {"add-field": fields}
            if self.logging_verbose >= 2:
                logger.info(f"Bulk creating fields {fields}")
            self._make_post(schema_url, request)
        else:
            for field in fields:
                request = {"add-field": field}
                if self.logging_verbose >= 2:
                    logger.info(f"Creating field {field['name']} with type {field['type']}")
                self._make_post(schema_url, request)

    def create_copyfields(self, copyfields, bulk=True):
        schema_url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        if bulk:
            request = {"add-copy-field": copyfields}
            if self.logging_verbose >= 2:
                logger.info(f"Bulk creating copyfields {copyfields}")
            self._make_post(schema_url, request)
        else:
            for copyfield in copyfields:
                request = {"add-copy-field": copyfield}
                if self.logging_verbose >= 2:
                    logger.info(f"Creating copyfield {copyfield['source']}-{copyfield['dest']}")
                self._make_post(schema_url, request)

    def delete_dynamic_fields(self, fields, bulk=True):
        schema_url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        if bulk:
            request = {"delete-dynamic-field": [{"name": field} for field in fields]}
            if self.logging_verbose >= 2:
                logger.info(f"Deleting dynamic fields {fields}")
            self._make_post(schema_url, request)
        else:
            for field in fields:
                request = {"delete-dynamic-field": {"name": field}}
                if self.logging_verbose >= 2:
                    logger.info(f"Deleting dynamic field {field}")
                self._make_post(schema_url, request)

    def add_dynamic_fields(self, dynamic_fields, bulk=True):
        schema_url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        if bulk:
            request = {"add-dynamic-field": dynamic_fields}
            if self.logging_verbose >= 2:
                logger.info(f"Bulk creating dynamic fields {dynamic_fields}")
            self._make_post(schema_url, request)
        else:
            for dynamic_field in dynamic_fields:
                request = {"add-dynamic-field": dynamic_field}
                if self.logging_verbose >= 2:
                    logger.info(f"Creating dynamic field {dynamic_field['name']} with type {dynamic_field['type']}")
                self._make_post(schema_url, request)

    def delete_field_types(self, field_types, bulk=True):
        schema_url = urljoin(self.base_url, f"/api/collections/{self.collection}/schema")
        if bulk:
            request = {"delete-field-type": [{"name": field_type} for field_type in field_types]}
            if self.logging_verbose >= 2:
                logger.info(f"Deleting field types {field_types}")
            self._make_post(schema_url, request)
        else:
            for field_type in field_types:
                request = {"delete-field-type": {"name": field_type}}
                if self.logging_verbose >= 2:
                    logger.info(f"Deleting field type {field_type}")
                self._make_post(schema_url, request)

    def create_collection_and_schema(self, delete_default_fields_definition, schema_definition, test_field_name):
        created = self.create_collection()
        if not created:
            has_field = self.check_collection_has_field(test_field_name)
            if has_field:
                if self.logging_verbose >= 1:
                    logger.info(f"Collection {self.collection} already exists, not creating")
                return
            else:
                if self.logging_verbose >= 1:
                    logger.info(f"Collection {self.collection} already exists, but no field {test_field_name}, going ahead with schema creation")

        if self.logging_verbose >= 1:
            logger.info("Delete unneeded fields")
        dynamic_fields = delete_default_fields_definition.get("deleteDynamicFields", [])
        if dynamic_fields:
            self.delete_dynamic_fields(dynamic_fields)

        if self.logging_verbose >= 1:
            logger.info("Delete unneeded field types")
        field_types = delete_default_fields_definition.get("deleteFieldTypes", [])
        if field_types:
            self.delete_field_types(field_types)

        if self.logging_verbose >= 1:
            logger.info("Create field types")
        field_types = schema_definition.get("fieldTypes", [])
        if field_types:
            self.add_field_types(field_types)

        if self.logging_verbose >= 1:
            logger.info("Create fields")
        fields = schema_definition["fields"]
        if fields:
            self.add_fields(fields)

        if self.logging_verbose >= 1:
            logger.info("Create dynamic fields")
        dynamic_fields = schema_definition.get("dynamicFields", [])
        if dynamic_fields:
            self.add_dynamic_fields(dynamic_fields)

        if self.logging_verbose >= 1:
            logger.info("Create copy fields")
        copyfields = schema_definition.get("copyFields", [])
        if copyfields:
            self.create_copyfields(copyfields)

    def collection_exists(self):
        if self.logging_verbose >= 1:
            logger.info(f"Checking if collection {self.collection} exists")
        url = urljoin(self.base_url, "api/collections")
        try:
            resp = requests.get(url, timeout=self.request_timeout)
            resp.raise_for_status()
            collections = resp.json().get("collections", [])
            return self.collection in collections
        except (RequestException, JSONDecodeError) as e:
            self._handle_request_exception(e, "checking if collection exists")

    def create_collection(self, configset=None):
        """Create a new Solr collection."""
        if self.collection_exists():
            if self.logging_verbose >= 1:
                logger.info(f"Collection {self.collection} already exists, not creating")
            return False

        url = urljoin(self.base_url, "api/collections")
        data = {"name": self.collection, "numShards": 1}
        if configset:
            data["config"] = configset
        self._make_post(url, data)
        if self.logging_verbose >= 1:
            logger.info(f"Created collection {self.collection}")
        self.disable_auto_data_driven_schema()
        return True

    def disable_auto_data_driven_schema(self):
        """Disable auto data driven schema for a collection."""
        url = urljoin(self.base_url, f"api/collections/{self.collection}/config")
        data = {"set-user-property": {"update.autoCreateFields": "false"}}
        self._make_post(url, data)
        if self.logging_verbose >= 1:
            logger.info(f"Disabled auto data driven schema for collection {self.collection}")

    def delete_collection(self):
        """Delete a Solr collection."""
        url = urljoin(self.base_url, f"api/collections/{self.collection}")
        try:
            resp = requests.delete(url, timeout=self.request_timeout)
            resp.raise_for_status()
            if self.logging_verbose >= 1:
                logger.info(f"Deleted collection {self.collection}")
        except (RequestException, JSONDecodeError) as e:
            self._handle_request_exception(e, "deleting collection")

    def create_collection_alias(self, alias):
        """Create a collection alias."""
        url = urljoin(self.base_url, "api/aliases")
        data = {"name": alias, "collections": [self.collection]}
        self._make_post(url, data)
        if self.logging_verbose >= 1:
            logger.info(f"Created collection alias {alias} for collection {self.collection}")
