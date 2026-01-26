"""Root model for OpenSOVD CDA Diagnostic Description."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from yaml_to_mdd.models.access_patterns import AccessPatterns
from yaml_to_mdd.models.dids import DIDs
from yaml_to_mdd.models.dtcs import DTCConfig, DTCs
from yaml_to_mdd.models.ecu import Ecu
from yaml_to_mdd.models.memory import MemoryConfig
from yaml_to_mdd.models.meta import Meta
from yaml_to_mdd.models.routines import Routines
from yaml_to_mdd.models.security import Security
from yaml_to_mdd.models.services import Services
from yaml_to_mdd.models.sessions import Sessions
from yaml_to_mdd.models.types import Types


class DiagnosticDescription(BaseModel):
    """Root model for OpenSOVD CDA Diagnostic Description YAML/JSON files.

    This is the top-level model that represents the entire diagnostic description
    document. It validates the schema version and contains references to all
    other sections of the document.

    Example:
    -------
        ```yaml
        schema: opensovd.cda.diagdesc/v1
        meta:
          author: "John Doe"
          domain: "Powertrain"
          ...
        ecu:
          id: "ECM_V1"
          name: "Engine Control Module"
          ...
        ```

    """

    model_config = ConfigDict(
        # Allow population by field name AND alias
        populate_by_name=True,
        # Forbid extra fields not defined in the model
        extra="forbid",
        # Use enum values instead of enum members for serialization
        use_enum_values=True,
        # Validate default values
        validate_default=True,
    )

    # Schema version identifier (required)
    # Using alias because "schema" is a reserved name in Pydantic
    schema_version: Annotated[
        Literal["opensovd.cda.diagdesc/v1"],
        Field(alias="schema", description="Schema version identifier"),
    ]

    # Required sections - Meta is now fully typed
    meta: Annotated[Meta, Field(description="Document metadata")]
    ecu: Annotated[Ecu, Field(description="ECU identification and addressing")]
    sessions: Annotated[Sessions, Field(description="Diagnostic session definitions")]
    services: Annotated[Services, Field(description="UDS service configurations")]
    access_patterns: Annotated[
        AccessPatterns | None,
        Field(default=None, description="Reusable access control patterns"),
    ]

    # Optional sections
    security: Annotated[
        Security | None,
        Field(default=None, description="Security access level definitions"),
    ]
    authentication: Annotated[
        Any | None,
        Field(default=None, description="Authentication configurations"),
    ]
    state_model: Annotated[
        Any | None,
        Field(default=None, description="ECU state model"),
    ]
    variants: Annotated[
        Any | None,
        Field(default=None, description="ECU variant definitions"),
    ]
    identification: Annotated[
        Any | None,
        Field(default=None, description="ECU identification data"),
    ]
    types: Annotated[
        Types | None,
        Field(default=None, description="Custom type definitions"),
    ]
    dids: Annotated[
        DIDs | None,
        Field(default=None, description="Data Identifier definitions"),
    ]
    routines: Annotated[
        Routines | None,
        Field(default=None, description="Control routine definitions"),
    ]
    dtc_config: Annotated[
        DTCConfig | None,
        Field(default=None, description="Global DTC configuration"),
    ]
    dtcs: Annotated[
        DTCs | None,
        Field(default=None, description="Diagnostic Trouble Code definitions"),
    ]
    memory: Annotated[
        MemoryConfig | None,
        Field(default=None, description="Memory region and data block configuration"),
    ]
    annotations: Annotated[
        Any | None,
        Field(default=None, description="Annotations and comments"),
    ]
    audience: Annotated[
        Any | None,
        Field(default=None, description="Target audience specification"),
    ]
    sdgs: Annotated[
        Any | None,
        Field(default=None, description="Special Data Groups"),
    ]
    comparams: Annotated[
        Any | None,
        Field(default=None, description="Communication parameters"),
    ]
    ecu_jobs: Annotated[
        Any | None,
        Field(default=None, description="ECU job definitions"),
    ]
    x_oem: Annotated[
        dict[str, Any] | None,
        Field(default=None, alias="x-oem", description="OEM-specific extensions"),
    ]
