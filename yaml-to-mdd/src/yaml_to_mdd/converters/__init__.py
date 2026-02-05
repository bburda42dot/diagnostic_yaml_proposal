"""Converters for transforming IR data into MDD binary format.

This package provides converters for the final stage of the conversion pipeline:
transforming the Intermediate Representation (IR) into MDD binary files.

MDD Format:
    The MDD (Marvelous Diagnostic Description) format is a two-layer structure:
    1. Container Layer (Protobuf): File metadata, version, chunks, signatures
    2. Data Layer (FlatBuffers): EcuData with DOPs, services, DTCs

Primary Classes:
    MDDWriter: Main class for writing MDD files
    IRToFlatBuffersConverter: Converts IR to FlatBuffers EcuData

Example:
-------
    >>> from yaml_to_mdd.converters import MDDWriter
    >>> from yaml_to_mdd.transform.transformer import YamlToIRTransformer
    >>>
    >>> # Assuming doc is a loaded DiagnosticDescription
    >>> ir_db = YamlToIRTransformer().transform(doc)
    >>>
    >>> # Write with default settings
    >>> writer = MDDWriter()
    >>> writer.write(ir_db, "output.mdd")
    >>>
    >>> # Write with compression
    >>> writer = MDDWriter(compression="gzip")
    >>> writer.write(ir_db, "output.mdd")
    >>>
    >>> # Get bytes without writing to file
    >>> mdd_bytes = writer.write_bytes(ir_db)

Compression Options:
    - None: No compression (default)
    - "gzip": Standard gzip compression
    - "zstd": Zstandard compression (requires zstandard package)


"""

from yaml_to_mdd.converters.flatbuffers_converter import IRToFlatBuffersConverter
from yaml_to_mdd.converters.mdd_reader import (
    MDDReader,
    MDDStructure,
    read_mdd_structure,
)
from yaml_to_mdd.converters.mdd_writer import MDDWriter, convert_yaml_to_mdd

__all__ = [
    "IRToFlatBuffersConverter",
    "MDDReader",
    "MDDStructure",
    "MDDWriter",
    "convert_yaml_to_mdd",
    "read_mdd_structure",
]
