from enum import Enum


class ProtectionType(str, Enum):
    NONE = "none"
    PASSWORD_PROTECTED = "password_protected"
    DRM_PROTECTED = "drm_protected"
    VIEWER_ONLY = "viewer_only"
    EXPORT_RESTRICTED = "export_restricted"
    POLICY_RESTRICTED = "policy_restricted"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    UPLOADED = "uploaded"
    METADATA_EXTRACTED = "metadata_extracted"
    PROTECTION_DETECTED = "protection_detected"
    BLOCKED_BY_PASSWORD = "blocked_by_password"
    BLOCKED_BY_DRM = "blocked_by_drm"
    AWAITING_MANUAL_REFINEMENT = "awaiting_manual_refinement"
    REFINED_UPLOADED = "refined_uploaded"
    READY_FOR_SEARCH = "ready_for_search"
    READY_FOR_VECTOR = "ready_for_vector"
    READY_FOR_RELATION = "ready_for_relation"
    PROCESSING_FAILED = "processing_failed"


class ProcessingCapability(str, Enum):
    METADATA_ONLY = "metadata_only"
    MANUAL_REFINED_ONLY = "manual_refined_only"
    FULLTEXT_EXTRACTABLE = "fulltext_extractable"
    CHUNKABLE = "chunkable"
    EMBEDDABLE = "embeddable"
    RELATION_EXTRACTABLE = "relation_extractable"


class DocumentType(str, Enum):
    OPERATION_MANUAL = "operation_manual"
    INSPECTION_PROCEDURE = "inspection_procedure"
    STARTUP_SHUTDOWN = "startup_shutdown"
    EMERGENCY_CONTACT = "emergency_contact"
    CONFIGURATION = "configuration"
    ACCOUNT_PERMISSION = "account_permission"
    CUSTOMER_POLICY = "customer_policy"
    INCIDENT_REPORT = "incident_report"
    WORK_REPORT = "work_report"
    CHANGE_LOG = "change_log"
    WORK_RESULT = "work_result"
    STARTUP_PROCEDURE = "startup_procedure"
    SLA = "sla"
    RESOURCE_STATUS = "resource_status"
    MONTHLY_REPORT = "monthly_report"
    RFP = "rfp"
    OTHER = "other"


class EventSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EventStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class AuditAction(str, Enum):
    SEARCH = "search"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DOWNLOAD = "document_download"
    GRAPH_QUERY = "graph_query"
    CHAT_REQUEST = "chat_request"
    ENRICH_REQUEST = "enrich_request"
    EVENT_VIEW = "event_view"
    REVIEW_CREATE = "review_create"
    REFINEMENT_UPLOAD = "refinement_upload"
    REFINEMENT_APPROVE = "refinement_approve"
    REPROCESS_REQUEST = "reprocess_request"
