import requests
from urllib.parse import urljoin


def get_collection_schema(base_url, collection):
    url = urljoin(base_url, f"/api/collections/{collection}/schema")
    res = requests.get(url)
    res.raise_for_status()
    return res.json()


def check_collection_has_field(base_url, collection, field):
    schema = get_collection_schema(base_url, collection)
    fields = schema['schema']['fields']
    for f in fields:
        if f['name'] == field:
            return True
    return False


def get_field_types(core_url, collection_name):
    schema = get_collection_schema(core_url, collection_name)
    return schema["schema"]["fieldTypes"]


def make_post(url, data):
    resp = requests.post(url, json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def add_field_types(api_url, field_types, bulk=True):
    if bulk:
        request = {"add-field-type": field_types}
        print(f"Creating field types {field_types}")
        make_post(api_url, request)
    else:
        for field_type in field_types:
            request = {"add-field-type": field_type}
            print(f"Creating field type {field_type['name']}")

def add_fields(api_url, fields, bulk=True):
    if bulk:
        request = {"add-field": fields}
        print(f"Creating fields {fields}")
        make_post(api_url, request)
    else:
        for field in fields:
            request = {"add-field": field}
            print(f"Creating field {field['name']} with type {field['type']}")
            make_post(api_url, request)


def create_copyfields(api_url, copyfields, bulk=True):
    if bulk:
        request = {"add-copy-field": copyfields}
        print(f"Creating copyfields {copyfields}")
        make_post(api_url, request)
    else:
        for copyfield in copyfields:
            request = {"add-copy-field": copyfield}
            print(f"Creating copyfield {copyfield['source']}-{copyfield['dest']}")
            make_post(api_url, request)


def delete_dynamic_fields(api_url, fields, bulk=True):
    if bulk:
        request = {"delete-dynamic-field": [{"name": field} for field in fields]}
        print(f"Deleting dynamic fields {fields}")
        make_post(api_url, request)
    else:
        for field in fields:
            request = {"delete-dynamic-field": {"name": field}}
            print(f"Deleting dynamic field {field}")
            make_post(api_url, request)


def add_dynamic_fields(api_url, dynamic_fields, bulk=True):
    if bulk:
        request = {"add-dynamic-field": dynamic_fields}
        print(f"Creating dynamic fields {dynamic_fields}")
        make_post(api_url, request)
    else:
        for dynamic_field in dynamic_fields:
            request = {"add-dynamic-field": dynamic_field}
            print(f"Creating dynamic field {dynamic_field['name']} with type {dynamic_field['type']}")
            make_post(api_url, request)


def delete_field_types(api_url, field_types, bulk=True):
    if bulk:
        request = {"delete-field-type": [{"name": field_type} for field_type in field_types]}
        print(f"Deleting field types {field_types}")
        make_post(api_url, request)
    else:
        for field_type in field_types:
            request = {"delete-field-type": {"name": field_type}}
            print(f"Deleting field type {field_type}")
            make_post(api_url, request)


def create_collection_and_schema(collection, schema_definition, test_field_name, solr_base_url):
    created = create_collection(solr_base_url, collection)
    if not created:
        has_field = check_collection_has_field(solr_base_url, collection, test_field_name)
        if has_field:
            print(f"Collection {collection} already exists, not creating")
            return
        else:
            print(f"Collection {collection} already exists, but no field {test_field_name}, going ahead with schema creation")

    schema_url = urljoin(solr_base_url, f"/api/collections/{collection}/schema")
    print("delete unneeded fields")
    dynamic_fields = schema_definition.get("deleteDynamicFields", [])
    if dynamic_fields:
        delete_dynamic_fields(schema_url, dynamic_fields)

    print("delete unneeded field types")
    field_types = schema_definition.get("deleteFieldTypes", [])
    if field_types:
        delete_field_types(schema_url, field_types)

    print("field types")
    existing_field_types = get_field_types(schema_url, collection)
    field_types = schema_definition.get("fieldTypes", [])
    if field_types:
        add_field_types(schema_url, field_types)

    print("fields")
    fields = schema_definition["fields"]
    if fields:
        add_fields(schema_url, fields)

    print("dynamic fields")
    dynamic_fields = schema_definition.get("dynamicFields", [])
    if dynamic_fields:
        add_dynamic_fields(schema_url, dynamic_fields)

    print("copy fields")
    copyfields = schema_definition.get("copyFields", [])
    if copyfields:
        create_copyfields(schema_url, copyfields)



def collection_exists(base_url, collection):
    print(f"Checking if collection {collection} exists")
    url = urljoin(base_url, "api/collections")
    resp = requests.get(url, timeout=10)
    return collection in resp.json()["collections"]


def create_collection(base_url, collection, configset=None):
    """Create a new Solr collection."""
    if collection_exists(base_url, collection):
        print(f"Collection {collection} already exists, not creating")
        return False

    url = urljoin(base_url, "api/collections")
    data = {"name": collection, "numShards": 1}
    if configset:
        data["config"] = configset
    resp = make_post(url, data)
    print(resp)
    disable_auto_data_driven_schema(base_url, collection)
    return True


def disable_auto_data_driven_schema(base_url, collection):
    """Disable auto data driven schema for a collection."""
    url = urljoin(base_url, f"api/collections/{collection}/config")
    data = {"set-user-property": {"update.autoCreateFields": "false"}}
    resp = make_post(url, data)
    print(resp)


def delete_collection(base_url, collection):
    """Delete a Solr collection."""
    url = urljoin(base_url, f"api/collections/{collection}")
    resp = requests.delete(url, timeout=10)
    print(resp)


def upload_configset(base_url, configset, file):
    url = urljoin(base_url, f"api/cluster/configs/{configset}")
    headers = {
        "Content-Type": "application/octet-stream",
    }

    with file as f:
        data = f.read()

    resp = requests.put(url, headers=headers, data=data)
    resp.raise_for_status()


def create_collection_alias(base_url, collection, alias):
    """Create a collection alias."""
    url = urljoin(base_url, "api/aliases")
    data = {"name": alias, "collections": [collection]}
    resp = make_post(url, data)
    print(resp)
