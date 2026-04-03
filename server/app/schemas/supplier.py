from app.schemas.common import AppBaseModel


class SupplierApplyRequest(AppBaseModel):
    supplier_name: str
    contact_name: str
    contact_phone: str
    qualification_desc: str | None = None
    base_product_price: float | None = None


class SupplierAgreementCreateRequest(AppBaseModel):
    agreement_type: str
    file_url: str


class ProductQualificationApplyRequest(AppBaseModel):
    product_id: int
    supplier_id: int | None = None
    qualification_type: str
    source_ref_id: int | None = None


class ProductQualificationAuditRequest(AppBaseModel):
    audit_status: str
    audit_remark: str | None = None
