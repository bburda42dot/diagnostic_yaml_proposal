"""YAML to IR (Intermediate Representation) transformation module.

This module transforms validated Pydantic models (from YAML/JSON) into an
Intermediate Representation (IR) that can be serialized to FlatBuffers.

The transformation process:
    1. Extract metadata (ECU name, revision, author)
    2. Process type definitions into DOPs (Data Object Properties)
    3. Generate read/write services for DIDs
    4. Generate routine services
    5. Process DTCs with snapshots and extended data
    6. Process memory regions

Primary Class:
    YamlToIRTransformer: Main transformer class

Example:
-------
    >>> from yaml_to_mdd.models import load_diagnostic_description
    >>> from yaml_to_mdd.transform import YamlToIRTransformer
    >>>
    >>> doc = load_diagnostic_description("my-ecu.yaml")
    >>> transformer = YamlToIRTransformer()
    >>> ir_db = transformer.transform(doc)
    >>>
    >>> # Inspect IR database
    >>> print(f"ECU: {ir_db.ecu_name}")
    >>> print(f"DOPs: {len(ir_db.dops)}")
    >>> print(f"Services: {len(ir_db.services)}")


"""

from yaml_to_mdd.transform.transformer import YamlToIRTransformer

__all__ = ["YamlToIRTransformer"]
