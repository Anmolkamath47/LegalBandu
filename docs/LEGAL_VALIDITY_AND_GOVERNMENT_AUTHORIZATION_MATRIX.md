# MANDATORY GOVERNMENT AUTHORIZATION AND LEGAL VALIDITY REQUIREMENTS — LEGALBANDU
**Document Reference:** LB-LEGAL-REG-2026-v1  
**Jurisdiction:** Republic of India  
**Applicable Legal Framework:** Indian Contract Act (1872), Information Technology Act (2000 & Amendments), Indian Stamp Act (1899), State Stamp Acts, Registration Act (1908), Notaries Act (1952), Customs Act (1962), and Insolvency & Bankruptcy Code (2016).

---

## 1. Executive Legal Posture & Regulatory Identity

### Platform Intermediary Distinction
1. **Legalbandu is a Technology Intermediary**, defined under **Section 2(1)(w) of the Information Technology Act, 2000**.
2. **Not a Government Department or Statutory Issuer:** Legalbandu does **not** have inherent statutory power to issue government bonds, generate government revenue stamps, register property, or act as a Certifying Authority (CA) under Section 24 of the IT Act.
3. **Approved Providers Required:** Where an instrument requires official e-stamping, electronic signature, information utility submission, or customs filing, Legalbandu must interface with authorized licensed entities:
   - **e-Stamping Central Record Keeping Agency (CRA):** Stock Holding Corporation of India Limited (SHCIL) or State e-Gras/Treasury Portals.
   - **Digital Document Execution (DDE) & Information Utility:** National E-Governance Services Limited (NeSL) under the Insolvency and Bankruptcy Code (IBC), 2016 and state revenue authorizations.
   - **eSign Service Providers (ESP):** Licensed by the Controller of Certifying Authorities (CCA) under Section 24 of the IT Act (e.g. Protean eGov Technologies / NSDL, C-DAC).
   - **Customs & Trade Gateway:** Directorate General of Systems and Data Management, Central Board of Indirect Taxes and Customs (CBIC) via ICEGATE.

---

## 2. Categorization of Legal Instruments & Exact Authorization Routes

| Category | Instrument Type | Governing Legislation | Competent Authority | Legalbandu Role | Permitted Execution Method | Stamping Requirement | Registration / Notarization | Official Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | **Private Commercial Agreement** (Service Agreement, Consulting, NDA, Freelance, MoU) | Indian Contract Act, 1872 (Sec 10, 2h); IT Act, 2000 (Sec 10A) | Civil Courts (Private Party Enforcement) | Technology Platform / Intermediary | Electronic Signatures (Aadhaar eSign, Class 3 DSC, or Mutual Digital Acceptance) | Stamping recommended under State Stamp Act (Article 5) to ensure admissibility under Sec 35 Stamp Act. | Registration optional under Section 18 Registration Act, 1908. Notarization optional. | Executed agreement PDF with cryptographically hashed audit trail (SHA-256). |
| **B** | **Commercial Contract Requiring Mandatory Stamp Duty** (Loan Agreement, Commercial Lease <1 yr, Indemnity Bond, Guarantee Deed) | Indian Stamp Act, 1899; State Stamp Acts (e.g. Maharashtra Stamp Act 1958, Karnataka Stamp Act 1957); IT Act 2000 | Superintendent of Stamps / Inspector General of Registration (IGR); SHCIL; NeSL | Technology Intermediary integrating with Authorized CRA/DDE Provider | Aadhaar eSign (ESP) / Class 3 DSC via CCA Certifying Authority following valid stamping | Mandatory electronic stamp certificate (SHCIL e-Stamp or NeSL DDE) with unique e-Stamp Certificate No. and GRN. | Optional registration unless term exceeds 11 months or creates encumbrance. | Verified e-Stamp Certificate + Digitalsignatures + NeSL DDE Transaction Identifier. |
| **C** | **Instrument Requiring Notarization or Registration** (Lease >1 year, Conveyance, Mortgage, Power of Attorney) | Transfer of Property Act, 1882 (Sec 107); Registration Act, 1908 (Sec 17, 32); Notaries Act, 1952 | Sub-Registrar of Assurances (SRO); Appointed Public Notaries | Document Drafting & Scheduling Intermediary (Physical SRO Guide) | **PHYSICAL IN-PERSON EXECUTION ONLY** (Except Maharashtra e-Registration / Karnataka Kaveri 2.0 where authorized) | Mandatory Stamp Duty based on state ad-valorem schedules. | **MANDATORY SRO REGISTRATION** under Section 17. In-person appearance with 2 witnesses. Remote online notarization is void under Indian law. | SRO Registered Deed with Registration Volume, Book No., Page No., and SRO Seal. |
| **D** | **Government-Administered / Statutory Bond** (Excise Bond, Surety Bond, Performance Guarantee for Public Tender, Court Bond) | Indian Contract Act (Sec 126); Statutory Department Acts (State Excise, Public Procurement, CPC/CrPC) | Relevant Government Department, Public Authority, or Competent Court | Facilitator / Preparer. Cannot issue or approve. | Wet-ink signature with physical stamp paper or approved bank guarantee (e-BG via NeSL) | Mandatory judicial or non-judicial stamp duty per court/department rules. | Notarization / Court verification by Oath Commissioner / Registrar where mandated. | Department Acknowledgement / Court Registry Endorsement with Official Inward Number. |
| **E** | **Specialized Electronic Customs e-Bond** (Customs Warehouse, Provisional Duty, EPCG, Advance Auth Bond) | Customs Act, 1962 (Sec 59, 143); CBIC Circular No. 19/2022-Customs; Circular No. 22/2023-Customs | Directorate General of Systems & Data Management (CBIC / ICEGATE) | Technical Form Preparer & Integration Bridge (Requires ICEGATE Trade Partner Onboarding) | Class 3 Digital Signature Certificate (DSC) on ICEGATE registered token or NeSL integrated eSign | Mandatory electronic stamping via NeSL integration with CBIC Customs Duty Pool. | Filed electronically via ICEGATE Customs EDI. Verified by Assistant/Deputy Commissioner of Customs. | Genuine ICEGATE Acknowledgement, NeSL Transaction ID, and Customs Bond Number (`CB-YYYY-XXXXX`). |

---

## 3. Statutory Electronic Document Exclusions (IT Act, 2000 — First Schedule)

Under **Section 1(4) read with the First Schedule of the Information Technology Act, 2000**, the provisions relating to electronic records and electronic signatures do **NOT** apply to the following instruments:

1. **Negotiable Instruments:** Any negotiable instrument (other than a cheque) as defined in Section 13 of the Negotiable Instruments Act, 1881 (Promissory notes, bills of exchange).
2. **Power of Attorney:** Any power-of-attorney as defined in Section 1A of the Powers-of-Attorney Act, 1882 (Except specific powers of attorney executed by financial entities licensed by RBI/SEBI/IRDAI under MeitY Notification S.O. 4488(E) dated 26.09.2022).
3. **Trusts:** Any trust as defined in Section 3 of the Indian Trusts Act, 1882.
4. **Wills:** Any will as defined in clause (h) of Section 2 of the Indian Succession Act, 1925, including any other testamentary disposition.
5. **Real Estate Contracts:** Any contract for the sale or conveyance of immovable property or any interest in such property (Requires physical execution, stamping, and SRO registration under Section 17 of the Registration Act, 1908).

### Mandatory System Control for Excluded Instruments:
- Electronic execution and click-signing are **strictly disabled**.
- The system flags the document with status: `LEGAL_REVIEW_REQUIRED` / `STATUTORY_EXCLUSION_IN-PERSON_ONLY`.
- The user is provided with a drafted printable legal template and clear SRO / Notary manual filing guidelines.
- The document is **never** labelled as "Electronically Executed".

---

## 4. Government Authorization & Provider Onboarding States

To prevent misrepresentation and maintain absolute integrity, every official integration is tracked in an Administrator-Only Register with 9 deterministic lifecycle states:

```
[NOT_ASSESSED]
       │
       ▼
[ELIGIBILITY_REVIEW_REQUIRED]
       │
       ▼
[APPLICATION_REQUIRED]
       │
       ▼
[APPLICATION_SUBMITTED]
       │
       ▼
[APPROVED_PENDING_INTEGRATION]
       │
       ▼
[PRODUCTION_VERIFIED] ◄── Requires genuine onboarding proof + live integration test
       │
 ┌─────┴──────────────────────┐
 ▼                            ▼
[EXPIRED]                 [SUSPENDED] / [REJECTED]
```

### Strict Operating Rules:
- **Rule 1:** Sandbox access is **not** government authorization. An integration in sandbox mode remains in `APPROVED_PENDING_INTEGRATION`.
- **Rule 2:** Only an authorized administrator can transition an integration to `PRODUCTION_VERIFIED` after verifying genuine contract/license reference numbers.
- **Rule 3:** Expired or suspended integrations are **automatically blocked** from processing live legal transactions.

---

## 5. Official ICEGATE & NeSL Customs e-Bond Workflow (11 Steps)

For specialized Category E instruments, Legalbandu executes the authentic 11-step sequence:

1. **Eligibility Verification:** Validate applicant's Importer Exporter Code (IEC), active PAN, GSTIN, and ICEGATE registered Customs Broker status.
2. **Particulars Collection:** Collect bonded warehouse details, port code (e.g. INNSA1 - Nhava Sheva), bond category (Warehousing Sec 59, Provisional Assessment Sec 18), and surety/bank guarantee details.
3. **Statutory Form & Declaration Validation:** Formulate statutory customs declarations (Form B-1/B-2) ensuring mandatory compliance clauses under Section 59/143 of Customs Act, 1962.
4. **Official Channel Selection:** Direct submission via NeSL DDE / ICEGATE e-Bond gateway.
5. **e-Stamping via Authorized CRA:** Procure digital stamp duty certificate through NeSL / State Revenue treasury.
6. **Class 3 DSC / eSign Execution:** Execute biometric or cryptographic digital signature using an approved CCA Certifying Authority token.
7. **ICEGATE Portal Dispatch:** Submit XML/JSON payload to ICEGATE customs gateway.
8. **Statutory Response Verification:** Poll for ICEGATE acknowledgment with digital customs stamp.
9. **Official Archival:** Store genuine ICEGATE Acknowledgement Reference, NeSL Transaction ID, and generated PDF hash (SHA-256).
10. **Granular Status Display:** Transition status strictly to `Officially accepted or issued` only when Customs Officer approves.
11. **Tamper-Evident Audit Trail:** Record complete chain-of-custody in immutable activity log.

---

## 6. The 15 Mandatory Lifecycle States

Legalbandu does **not** collapse legal workflows into a single generic green badge. Every instrument progresses through 15 transparent, auditable states:

1. `Draft — not executed`
2. `Legal review required`
3. `Ready for stamping`
4. `Stamping pending`
5. `Stamped — genuine applicable evidence verified`
6. `Awaiting signatures`
7. `Signed — signature evidence verified`
8. `Execution requirements pending`
9. `Executed — applicable execution checks passed`
10. `Registration pending`
11. `Registered — genuine registration evidence verified`
12. `Official submission pending`
13. `Submitted to official platform`
14. `Officially accepted or issued — only with verified supporting evidence`
15. `Completed — all applicable requirements tracked for this instrument are satisfied`

---

## 7. Mandatory Legal Validity Checks Checklist

Before any agreement or bond can be finalized, the Legalbandu Compliance Engine verifies:
- [ ] **Classification Check:** Valid category (A, B, C, D, E) verified against transaction scope.
- [ ] **Signatory Capacity & Authority:** Board resolution / POA / Individual legal age (18+) verified.
- [ ] **Consideration & Lawful Purpose:** Section 10 & 23 Indian Contract Act compliance verified.
- [ ] **Exclusion Verification:** Confirmed instrument does not violate IT Act First Schedule.
- [ ] **Stamp Duty Verification:** Verified state-specific stamp duty rate and genuine certificate number.
- [ ] **Signature Verification:** Approved eSign method (IT Act Sec 3A / 5) or physical execution notice.
- [ ] **Registration Formalities:** SRO registration requirement assessed and documented.
- [ ] **Professional Legal Judgment Flag:** Unresolved or ambiguous terms flagged for legal counsel.
