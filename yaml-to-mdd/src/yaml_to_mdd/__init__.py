"""yaml-to-mdd: Converter from OpenSOVD CDA Diagnostic Description YAML to MDD binary format.

This package provides tools for:
- Loading and validating YAML/JSON diagnostic descriptions
- Transforming to an Intermediate Representation (IR)
- Converting to MDD (FlatBuffers + Protobuf) binary format

Quick Start:
    >>> from yaml_to_mdd.models import load_diagnostic_description
    >>> from yaml_to_mdd.transform.transformer import YamlToIRTransformer
    >>> from yaml_to_mdd.converters import MDDWriter
    >>>
    >>> doc = load_diagnostic_description("my-ecu.yaml")
    >>> ir_db = YamlToIRTransformer().transform(doc)
    >>> MDDWriter().write(ir_db, "my-ecu.mdd")

Modules:
    models: Pydantic models for YAML schema validation
    transform: YAML to IR transformation
    converters: IR to MDD (FlatBuffers/Protobuf) conversion
    validation: Semantic validation beyond schema
    filter: Audience filtering
    ir: Intermediate Representation data structures
    cli: Command-line interface
"""

__version__ = "0.1.0"
