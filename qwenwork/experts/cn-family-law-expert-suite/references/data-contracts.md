# 结构化工作底稿

## matter

`matter_id / jurisdiction / analysis_as_of / request_mode / relationship / goal / deliverable / deadline / status / owner / lawyer_approver / safety_status / conflict_status`

## known_field

`field_id / field_name / value / source_type / source_id / source_locator / reliability / conflict_status / sufficient_for_current_output / last_updated`

提问前以本表去重。`sufficient_for_current_output=true` 的字段不得再次向用户获取；材料来源属于当事人陈述时保留该事实层级，不以重复提问代替证据核验。

## party

`party_id / role / name / id_masked / capacity / marital_status / contact_masked / representation / consent_status / conflict_note`

## fact_record

`fact_id / proposition / fact_status / source_ids / source_locator / asserted_by / contrary_source_ids / confidence / materiality / verification_action / approved_for_drafting`

## document_record

`document_id / filename / type / date / provider / version / hash / page_count / integrity / sensitive_data / extraction_status / reviewer`

## evidence_record

`evidence_id / document_id / locator / supported_fact_ids / limits / authenticity_status / original_or_copy / conflict_ids / confidentiality`

## asset_record

`asset_id / category / description / registered_owner / claimed_owner / controller / acquisition_date / acquisition_method / source_of_funds / relationship_stage / evidence / value / valuation_date / encumbrance / co_owner / third_party_interest / current_characterization / confidence / agreed_owner / agreed_share / equalization_payment / implementation_action / deadline / consent / registration_status`

## debt_record

`debt_id / creditor / nominal_debtor / guarantor / contract_date / amount / balance / purpose / fund_flow / benefit_destination / joint_signature / ratification / creditor_knowledge / household_need / joint_operation / security / external_liability / internal_allocation / agreed_payer / reimbursement / deadline / release_document / creditor_consent_needed / dispute_status`

## child_record

`child_id / name_masked / birth_date / health / school / residence / current_care / wishes_consideration / special_needs / own_property / safety_issue`

## authority_record

按 [authority-baseline.md](authority-baseline.md) 的字段执行。

## issue_record

`issue_id / question / related_fact_ids / related_authority_ids / positions / provisional_conclusion / confidence / consequence / options / lawyer_decision`

## drafting_instruction

`clause_id / objective / approved_fact_ids / prohibited_content / selected_variant / conditions / performance_action / attachment / open_item / approver`

## approval_record

`approval_id / deliverable_version / approver_name_or_team / professional_capacity / approval_scope / decision / conditions / approved_at / source_id / source_locator`

没有可定位的 `approval_record` 时，不得将状态标为 `lawyer_approved` 或 `final`。

所有表之间使用稳定 ID 关联；不得复制后形成互不一致的事实版本。
