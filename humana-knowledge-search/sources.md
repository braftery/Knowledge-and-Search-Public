# Sources: Governed Knowledge and Search research corpus

> **Public copy:** this document refers to internal working files (such as the research notes and local copies of sources; each source below is listed with its link) that are not included in this public copy of the repository.

Status: APPROVED 2026-11-02 with changes. HDI and TSIA dropped. Palantir 5.13 replaced and 5.36 added (see LG5).
Prepared: 2026-11-02.

## Setup record

**Jev test call (2026-11-02).** One `jev_noul` call. Proposition: "This passage states a specific fact about Medicare communications requirements." Context was a one-sentence test passage about 42 CFR 422.2267(e). Result: status `ok`, model `jev-1.14.0`, probability 0.95, label `likely`, auto true, threshold 0.85. The connector responds.

**How the scoping and enumeration were done.** I used web search and URL status checks only, to find and check sources. One page (the CX Today Magic Quadrant rundown) was opened with WebFetch to list vendors. Nothing below counts as a reading for any learning goal. Every score in the scoping tables rests on search-result snippets and vendor pages. Treat them as orientation evidence, not findings. Nothing here goes to Jev, because the plan skips Jev for orientation reads.

**Access risks already seen.** These returned 403, a Cloudflare challenge, a form gate, or 404 when I checked the URL. Readers will retry them and log what happens: CRT decision site and CanLII (403 to curl), Gartner (bot challenge, paywalled), eGain pages (Cloudflare), HHS strategy page (403 to curl), TSIA (404 on the free page found), DITAWriter (406), McKinsey (timeout).

---

## Learning Goal 5 scoping pass

Scale: H = strong evidence, M = some evidence, L = little or none found. Criteria:
- (1) relevance to governed, cited, permission-scoped knowledge;
- (2) documented deployments in healthcare, insurance, or another regulated industry;
- (3) depth of public documentation on permissions, citation, and approval;
- (4) presence in large enterprise contact centers.

### Enterprise search segment

| Company | (1) | (2) | (3) | (4) | Evidence |
|---|---|---|---|---|---|
| Glean | H | L | H | M | Docs say the user's identity is checked against source-system permissions at query time, and documents the user cannot open are never used as context or cited ([docs](https://docs.glean.com/security/security-principles)). The healthcare page is marketing and names no customer ([page](https://glean.com/industries/healthcare)). |
| Microsoft 365 Copilot | M | L | H | H | Microsoft publishes an oversharing deployment blueprint, which shows that inherited over-permissioning is the documented failure mode ([Learn](https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-blueprint-oversharing)). No named insurer rollout found. |
| Google Gemini Enterprise (formerly Agentspace) | M | M | H | M | Docs cover ACL ingestion, identity sync, and an access-control setting that cannot be changed after a data store is created ([connectors](https://docs.cloud.google.com/gemini/enterprise/docs/introduction-to-connectors-and-data-stores), [custom connector](https://docs.cloud.google.com/gemini/enterprise/docs/custom-connector)). Humana's Agent Assist runs on Google's Gemini Enterprise for CX stack ([Humana](https://news.humana.com/news/articles/humana-redefines-the-member-experience-with-agent-assist-built-with-google-cloud)). |
| Coveo | H | M | H | M | Docs on security identities and item permissions at index and query time, plus a page on RGA data security ([secured search](https://docs.coveo.com/en/1749/), [RGA security](https://docs.coveo.com/en/nbpd4153/)). A Humana case study is listed, with a headline only ([listing](https://www.casestudies.com/company/coveo/case-study/humana-ai-driven-relevance-for-customer-centric-healthcare)). Manulife is listed too. |
| Elastic | M | L | M | L | Named a Leader in the Forrester Wave for cognitive search, Q4 2025 ([Elastic](https://www.elastic.co/es/blog/forrester-leader-cognitive-search-platforms-2025)). It is a toolkit, not a governed answer product. |
| Kore.ai | M | L | M | M | Named a Forrester Leader, Q4 2025 (vendor-stated, [Kore.ai](https://www.kore.ai/news/kore-ai-named-a-leader-in-cognitive-search-platforms-q4-2025-evaluation)). It overlaps with agent platforms. |
| Mindbreeze | M | L | M | L | Named a Forrester Leader ([Mindbreeze](https://www.mindbreeze.com/news/independent-research-firm-names-mindbreeze-a-leader-in-the-cognitive-search-platforms)). Its customers are mostly European. |
| Lucidworks, Amazon Q Business, Atlassian Rovo, GoSearch | L to M | L | M | L | They appear only in competitor roundups, which are often vendor-authored ([example](https://www.gosearch.ai/faqs/top-glean-competitors-in-2026/)). |

**Recommended (4):**
- **Glean.** It is the reference design for permission-aware retrieval and has the clearest public docs on mirroring permissions. *Contrast case:* it searches ungoverned drives, which the case puts out of scope.
- **Microsoft 365 Copilot.** It has the largest enterprise footprint, and Microsoft's own oversharing guidance documents what goes wrong when permissions are inherited from ungoverned content. *Contrast case.*
- **Google Gemini Enterprise.** Its ACL docs are detailed, and Google's stack runs a disclosed agent-assist deployment at a Medicare Advantage payer (Humana). *Partial analog for permission scoping; contrast case for content governance.*
- **Coveo.** It is built for customer service, documents cited generative answers and index-level security, and lists Humana as a customer. *Partial analog for scoped, cited retrieval.*

**Not chosen.** Elastic, Kore.ai, and Mindbreeze lead the Forrester Wave, but I found no payer deployments, and their public docs say less about citation and approval than the four above. The rest appear only in vendor-written roundups.

### Contact center knowledge segment

| Company | (1) | (2) | (3) | (4) | Evidence |
|---|---|---|---|---|---|
| eGain | H | M | M | H | Leader in Gartner's first Magic Quadrant for customer service knowledge management, July 2026 ([CX Today](https://cxtoday.com/gartner-magic-quadrant-customer-service-knowledge-management-2026)). It has a health-plan suite and an unnamed "leading US health insurer" (company-stated, [release](https://egain.com/?p=10214)). Allegiance, a Cigna company, selected it in 2022 ([GlobeNewswire](https://www.globenewswire.com/fr/news-release/2022/08/30/2506516/0/en/Allegiance-a-Cigna-Company-selects-eGain-for-knowledge-powered-digital-engagement.html)). |
| Verint | M | H | M | H | Named UnitedHealth Group deployment: more than 80,000 articles and more than 40,000 users, with a Medicare Stars rating at risk (company-stated, [Verint](https://www.verint.com/case-studies/unitedhealth-group-capitalizes-on-millions-of-data-points-with-verint-knowledge-management/)). Also lists BCBS Louisiana and a Humana case ([listing](https://www.casestudies.com/company/verint-systems/case-study/humana-customer-case-study)). It did not appear in the Gartner rundown. |
| Salesforce Knowledge | M | M | H | H | Gartner Leader. Developer docs cover article versions and data categories that control access ([dev guide](https://developer.salesforce.com/docs/atlas.en-us.knowledge_dev.meta/knowledge_dev/knowledge_development_object_managing_articles.htm)). Approval processes are documented. |
| Shelf | H | M | M | M | Gartner Leader, cited for diagnostics on outdated, duplicate, and compliance-risk content ([CX Today](https://cxtoday.com/gartner-magic-quadrant-customer-service-knowledge-management-2026)). Help docs define conflicting answers ([help](https://help.shelf.io/advanced-scores-in-content-intelligence-5983adf3)). Has an unnamed Fortune 50 healthcare case and a PBM case (company-stated). |
| NICE (CXone Expert) | M | M | M | H | Gartner Challenger. Governance and answer auditability are named as strengths, with the caution that it is sold as a CXone add-on ([CX Today](https://cxtoday.com/gartner-magic-quadrant-customer-service-knowledge-management-2026)). Payer deployments found (AOK Bayern) are for the CXone platform, not Expert ([NICE](https://www.nice.com/press-releases/aok-bayern-transforms-healthcare-service-for-4-5-million-members-with-nices-cxone-cx-ai-platform)). |
| ServiceNow Knowledge Management | M | L | H | M | Docs cover approval workflows and user-criteria scoping ([docs](https://www.servicenow.com/docs/r/servicenow-platform/knowledge-management/r_KnowledgeWorkflows.html)). Focused on IT service management. No payer contact center deployment found. |
| Guru | M | L | M | L | A verification workflow exists ([features](https://www.getguru.com/es/features/verification)). No health insurer case found. Not in the Gartner rundown. |
| KMS Lighthouse, Upland (Panviva), Talkdesk, USU | M | M | L to M | M | Gartner Niche Players and a Visionary. Deployments include Delta Dental of Washington (KMS) and Bupa (Panviva). |

**Recommended (4):**
- **eGain.** Gartner Leader with a health-plan product and payer deployments, though company-stated. *Direct analog.*
- **Verint.** It has the only named large US payer deployment found, at UnitedHealth Group, with Medicare Stars context. *Direct analog.*
- **Salesforce Knowledge.** It has the deepest public docs on versioning, approval, and data-category scoping, and is widely deployed. *Partial analog for the approval and version model.*
- **Shelf.** It is the only finalist whose core pitch is spotting duplicate and conflicting content, which is the failure in the case. *Partial analog for drift and deduplication.*

**Not chosen.** NICE scores close on governance, but its knowledge product sells as a CXone add-on and I found no Expert-specific payer deployment. Reader to note it as an alternative. ServiceNow's docs are strong, but it is IT-focused. Guru has no regulated deployment I could find. The Niche Players have thin documentation.

### Health insurer precedents (no selection step; all candidates found)

Humana Agent Assist; UnitedHealthcare Avery; Elevance associate tools; Independence Blue Cross GenAI pilot; Oscar Health care-guide copilot. Every one is company-stated unless trade press reports independently.

### Palantir boundary

15 sources: 9 documentation pages, the FY2025 annual report, 4 deployment sources, and 1 criticism source. Documentation covers each page's own text and no linked subpages.

---

## Corpus by learning goal

Totals: LG1 13, LG2 12, LG3 19, LG4 13, LG5 36. That is 93 sources.

### Learning Goal 1 (13)

| # | Source | URL | Note |
|---|---|---|---|
| 1.1 | KCS v6 Practices Guide, Section 2: The KCS Practices (Solve and Evolve loops, Content Health) | https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030 | Section page only |
| 1.2 | KCS v6 Practices Guide, Appendix C: Metrics Matrix | https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/070 | |
| 1.3 | KCS Measurement Matters v6 | https://library.serviceinnovation.org/KCS/KCS_v6/Measurement_Matters_v6 | Landing page plus at most 4 child pages on content health and outcome measures |
| 1.4 | Article Quality Index is now Content Standard Checklist | https://www.serviceinnovation.org/aqi-is-content-standard-checklist/ | |
| 1.5 | KCS case study: Progress Software | https://library.serviceinnovation.org/Case_Studies/KCS_Case_Studies/850_Progress_Software_KCS_in_Application_Support_Services | Named adopter |
| 1.6 | KCS case study: Omgeo (financial services), Evolve Loop | https://library.serviceinnovation.org/Case_Studies/KCS_Case_Studies/725_Omgeo_Improving_CX_with_KCS_Evolve_Loop | Regulated analog |
| 1.7 | KCS case study: ServiceNow, Faster Time to Relief | https://library.serviceinnovation.org/Case_Studies/KCS_Case_Studies/400_ServiceNow_KCS_Faster_Time_to_Relief | Named adopter |
| 1.8 | Call Centre Helper, "Finding Information Quickly Is the Biggest Challenge" (2021 survey, n=224) | https://www.callcentrehelper.com/finding-information-quickly-is-the-biggest-challenge-209541.htm | Pre-2022, vendor-sponsored; used for causes of decay |
| 1.9 | Brynjolfsson, Li, Raymond, "Generative AI at Work," NBER w31161 | https://www.nber.org/papers/w31161 | Outcome evidence from a contact center |
| 1.10 | Salesforce, State of Service, 7th edition (PDF) | https://www.salesforce.com/en-us/wp-content/uploads/sites/4/documents/PDF/state-of-service-7th-edition.pdf | Company survey |
| 1.11 | McKinsey, "Where is customer care in 2024?" | https://www.mckinsey.com/capabilities/operations/our-insights/where-is-customer-care-in-2024 | Timed out when checked |
| 1.12 | Gartner, Magic Quadrant for Customer Service KMS, abstract (2026) | https://www.gartner.com/en/documents/8131229 | Expect paywall; abstract only |
| 1.13 | Shelf case study: Fortune 50 healthcare, "60% content rot" | https://www.casestudies.com/company/shelf-09/case-study/healthcare-eliminates-60-content-rot-and-reaches-95-fcr-with-shelf | Company-stated decay figure |

HDI and TSIA: dropped at sign-off.

### Learning Goal 2 (12)

| # | Source | URL | Note |
|---|---|---|---|
| 2.1 | OASIS DITA 1.3, Part 0: Overview | https://docs.oasis-open.org/dita/dita/v1.3/dita-v1.3-part0-overview.html | |
| 2.2 | DITA 1.3 spec 2.4.2: Content reference (conref) | https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part3-all-inclusive/archSpec/base/conref.html | Reuse mechanism |
| 2.3 | DITA 1.3 spec 2.4.2.1: Conref overview | https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part3-all-inclusive/archSpec/base/conref-overview.html | |
| 2.4 | RWS Tridion Docs, HORIBA Medical case study (PDF) | https://rws.com/media/images/tridion-docs-horiba-medica-case-study-rws-en-a4_tcm228-205235.pdf | Company-stated; reuse figures conflict across RWS sources |
| 2.5 | Bluestream, GE Healthcare DITA case study | https://bluestream.com/case-studies/ge-healthcare/ | Company-stated |
| 2.6 | DITAWriter, "DITA in the Healthcare Sector" (Carestream interview) | https://ditawriter.com/dita-in-the-healthcare-sector | Practitioner account, FDA-regulated; returned 406 when checked |
| 2.7 | Veeva PromoMats 2024 Innovation Guide (PDF) | https://www.veeva.com/wp-content/uploads/2024/01/Promomats_Innovation-Guide_v7.pdf | Modular content and claims library sections only |
| 2.8 | Veeva, "Modular Content Powers Omnichannel Engagement at Speed and Scale" (2023 PDF) | https://pantheon.veeva.com/wp-content/uploads/2023/02/NA-Modular-Content-Powers-Omnichannel-Engagement-at-Speed-and-Scale.pdf | |
| 2.9 | Veeva, "Optimize MLR Workflows Using a Central Claims Library" | https://www.veeva.com/resources/optimize-mlr-workflows-using-a-central-claims-library/ | Company-stated figures |
| 2.10 | Veeva blog, Astellas and Merck KGaA MLR teams on modular content | https://www.veeva.com/blog/how-astellas-merck-kgaa-mlr-teams-view-the-modular-content-evolution | Named adopters |
| 2.11 | Klick, "From Checkpoint to Input: A Different Model for MLR" | https://idx.klick.com/articles/from-checkpoint-to-input-a-different-model-for-mlr | Agency-stated case |
| 2.12 | FDA, Structured Product Labeling Resources | https://www.fda.gov/industry/fda-data-standards-advisory-board/structured-product-labeling-resources | Landing page plus at most 2 linked FDA pages that define SPL versioning |

### Learning Goal 3 (19)

| # | Source | URL | Note |
|---|---|---|---|
| 3.1 | Moffatt v. Air Canada, 2024 BCCRT 149 | https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do (fallback: https://www.canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html) | Both gave 403 to curl |
| 3.2 | The Markup, "NYC's AI Chatbot Tells Businesses to Break the Law" (2024) | https://themarkup.org/news/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law | Government incident |
| 3.3 | Magesh et al., "Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools" (2024) | https://arxiv.org/abs/2405.20362 | Regulated-domain RAG measured |
| 3.4 | Barnett et al., "Seven Failure Points When Engineering a RAG System" (2024) | https://arxiv.org/abs/2401.05856 | |
| 3.5 | Chen et al., "Benchmarking LLMs in Retrieval-Augmented Generation" (RGB, 2023) | https://arxiv.org/abs/2309.01431 | Negative rejection, counterfactual robustness |
| 3.6 | Wu et al., "ClashEval" (2024) | https://arxiv.org/abs/2404.10198 | Conflicting evidence |
| 3.7 | Liu et al., "Lost in the Middle" (2023) | https://arxiv.org/abs/2307.03172 | |
| 3.8 | Gao et al., "Enabling LLMs to Generate Text with Citations" (ALCE, 2023) | https://arxiv.org/abs/2305.14627 | Citation accuracy |
| 3.9 | Liu, Zhang, Liang, "Evaluating Verifiability in Generative Search Engines" (2023) | https://arxiv.org/abs/2304.09848 | Unsupported citations |
| 3.10 | Joren et al., "Sufficient Context" (2024) | https://arxiv.org/abs/2411.06037 | Abstention |
| 3.11 | Wen et al., "Know Your Limits: A Survey of Abstention in LLMs" (2024) | https://arxiv.org/abs/2407.18418 | |
| 3.12 | Anthropic, "Introducing Contextual Retrieval" (2024) | https://www.anthropic.com/news/contextual-retrieval | Hybrid BM25 plus embeddings plus reranker, measured; vendor-published |
| 3.13 | Qu et al., "Is Semantic Chunking Worth the Computational Cost?" (2024) | https://arxiv.org/abs/2410.13070 | Chunking |
| 3.14 | Es et al., "RAGAS" (2023) | https://arxiv.org/abs/2309.15217 | Eval metrics |
| 3.15 | Saad-Falcon et al., "ARES" (2023) | https://arxiv.org/abs/2311.09476 | Eval metrics |
| 3.16 | Jacovi et al., "The FACTS Grounding Leaderboard" (2025) | https://arxiv.org/abs/2501.03200 | Grounding benchmark |
| 3.17 | NIST AI 600-1, Generative AI Profile (PDF) | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf | Sections on confabulation, information integrity, and pre-deployment testing only |
| 3.18 | OWASP LLM08:2025, Vector and Embedding Weaknesses | https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/ | Permission leakage |
| 3.19 | Microsoft Learn, Azure AI Search security trimming | https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search | Pre-filter versus post-filter |

### Learning Goal 4 (13, one over range)

Item 4.13 is the reason for going over: question 5 asks for HHS guidance, which no CMS source covers.

| # | Source | URL | Note |
|---|---|---|---|
| 4.1 | 42 CFR 422.2260, Definitions (communications versus marketing) | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-V/section-422.2260 | |
| 4.2 | 42 CFR 422.2267, Required materials and content | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-V/section-422.2267 | |
| 4.3 | 42 CFR 423.2267, Part D required materials and content | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-V/section-423.2267 | |
| 4.4 | 42 CFR 422.2274, Agent, broker, and TPMO requirements (call recording) | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-V/section-422.2274 | |
| 4.5 | 42 CFR 422.504, Contract provisions (record retention, paragraph (d)) | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-K/section-422.504 | Paragraph (d) and related paragraphs only |
| 4.6 | CMS Medicare Communications and Marketing Guidelines page, and the latest MCMG PDF it links (3-16-2022) | https://www.cms.gov/medicare/health-drug-plans/managed-care-marketing/medicare-guidelines | The page has not posted a newer MCMG |
| 4.7 | CY2027 MA and Part D final rule, Federal Register 2026-06600 (April 6, 2026) | https://www.federalregister.gov/documents/2026/04/06/2026-06600 | Marketing and communications sections only |
| 4.8 | CMS Part C and Part D Enforcement Actions page | https://cms.gov/Medicare/Compliance-and-Audits/Part-C-and-Part-D-Compliance-and-Audits/PartCandPartDEnforcementActions-.html | Index; cites the CMP letters it lists |
| 4.9 | CMS CMP letter, Aetna (2015), inaccurate pharmacy network information | https://www.cms.gov/Medicare/Compliance-and-Audits/Part-C-and-Part-D-Compliance-and-Audits/Downloads/AetnaCMP4162015.pdf | Named case |
| 4.10 | CMS CMP letter, InnovaCare (2013), inaccurate ANOC | https://www.cms.gov/Medicare/Compliance-and-Audits/Part-C-and-Part-D-Compliance-and-Audits/Downloads/InnovaCare-Inc-CMP-10_-24_13.pdf | Named case |
| 4.11 | CMS 2025 Part C and Part D Program Audit and Enforcement Report | https://www.cms.gov/files/document/2025-part-c-part-d-program-audit-enforcement-report.pdf | |
| 4.12 | CMS 2022 Part C and Part D Call Center Monitoring memo | https://cms.gov/files/document/2022partcandpartdcallcentermonitoring.pdf | Accuracy of customer service rep answers |
| 4.13 | CMS FAQ on coverage criteria and use of algorithms and AI, Feb 6, 2024 (AAMC-hosted copy); HHS AI Strategy, Dec 4, 2025 | https://www.aamc.org/media/74896/download?attachment ; https://www.hhs.gov/press-room/hhs-unveils-ai-strategy-to-transform-agency-operations.html | No cms.gov copy found; the reader will look for one first |

The Indiana University Health Plans CMP (2015) is available as a third named case if 4.9 and 4.10 prove too thin.

### Learning Goal 5 (36, one over range)

Item 5.36 is the reason for going over: you asked for an HHS Protect source in addition to the 5.13 replacement.

**Palantir (15)**

| # | Source | URL |
|---|---|---|
| 5.1 | Ontology overview | https://www.palantir.com/docs/foundry/ontology/overview/ |
| 5.2 | Ontology core concepts | https://www.palantir.com/docs/foundry/ontology/core-concepts/ |
| 5.3 | Action types overview | https://www.palantir.com/docs/foundry/action-types/overview/ |
| 5.4 | Markings concepts | https://www.palantir.com/docs/foundry/security/markings/ |
| 5.5 | Object permissioning overview | https://www.palantir.com/docs/foundry/object-permissioning/overview/ |
| 5.6 | Data Lineage overview | https://www.palantir.com/docs/foundry/data-lineage/overview/ |
| 5.7 | AIP Logic overview, and AIP security and privacy | https://www.palantir.com/docs/foundry/logic/overview/ ; https://www.palantir.com/docs/foundry/aip/aip-security/ |
| 5.8 | AIP Evals overview | https://www.palantir.com/docs/foundry/aip-evals/overview/ |
| 5.9 | Palantir FY2025 Annual Report (Form ARS) | https://www.sec.gov/Archives/edgar/data/0001321655/000132165526000021/fy2025palantirars.pdf (business description, healthcare, and risk-factor sections only) |
| 5.10 | Cognizant and Palantir TriZetto partnership (Feb 5, 2026) | https://news.cognizant.com/2026-02-05-Cognizant-partners-with-Palantir-to-Accelerate-AI-Driven-Modernization-in-Healthcare-and-Enterprise-Operations |
| 5.11 | GNP Seguros expansion of Foundry and AIP (insurer, health line) | https://secure.businesswire.com/news/home/20260707514163/en/Palantir-Expands-Its-Presence-in-Mexico-and-Strengthens-Its-AI-Offering-in-the-Insurance-Sector-with-GNP-Seguros |
| 5.12 | NHS England, Federated Data Platform: evaluating benefits | https://www.england.nhs.uk/digitaltechnology/nhs-federated-data-platform/impact/fdp-uptake-and-benefits/evaluating-benefits/ (independent coverage to pair: https://www.theregister.com/2025/05/16/nhs_hospitals_palantir/) |
| 5.13 | AIP Document Intelligence overview (document extraction into Foundry: extraction strategies, evaluation, deployment) | https://www.palantir.com/docs/foundry/document-intelligence/overview/ |
| 5.14 | HASH, "The problem with Palantir" | https://hash.ai/blog/the-problem-with-palantir (labeled as an interested-party critique) |
| 5.36 | GAO-21-600, "COVID-19: HHS's Collection of Hospital Capacity Data" (Aug 2021). Independent audit of HHS Protect: reporting changes, data quality, and how stakeholders used the data | https://www.gao.gov/products/gao-21-600 (fallback: https://collections.nlm.nih.gov/catalog/nlm:nlmuid-9918317488206676-pdf). GAO returned 403 to curl. Palantir is not named in the search snippets, so if the report does not name it, the reader must log the Palantir attribution as unverified from this source |

**Enterprise search (8)**

| # | Source | URL |
|---|---|---|
| 5.15 | Glean security principles | https://docs.glean.com/security/security-principles |
| 5.16 | Glean healthcare page | https://glean.com/industries/healthcare |
| 5.17 | Microsoft 365 Copilot oversharing blueprint | https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-blueprint-oversharing |
| 5.18 | Microsoft blog, mitigating oversharing to govern Copilot and agents | https://techcommunity.microsoft.com/blog/microsoft365copilotblog/mitigate-oversharing-to-govern-microsoft-365-copilot-and-agents/4448744 |
| 5.19 | Gemini Enterprise, connectors and data stores | https://docs.cloud.google.com/gemini/enterprise/docs/introduction-to-connectors-and-data-stores |
| 5.20 | Gemini Enterprise, custom connector ACLs | https://docs.cloud.google.com/gemini/enterprise/docs/custom-connector |
| 5.21 | Coveo, Basic secured search, and RGA data security | https://docs.coveo.com/en/1749/ ; https://docs.coveo.com/en/nbpd4153/ |
| 5.22 | Coveo Humana case study | https://www.casestudies.com/company/coveo/case-study/humana-ai-driven-relevance-for-customer-centric-healthcare |

**Contact center knowledge (8)**

| # | Source | URL |
|---|---|---|
| 5.23 | eGain AI Knowledge Suite for Health Plans | https://www.egain.com/?p=37810 (Cloudflare risk) |
| 5.24 | eGain release, leading US health insurer selects eGain | https://egain.com/?p=10214 |
| 5.25 | Verint, UnitedHealth Group case study | https://www.verint.com/case-studies/unitedhealth-group-capitalizes-on-millions-of-data-points-with-verint-knowledge-management/ |
| 5.26 | Verint, UnitedHealth Group standardizes enterprise-wide | https://verint.com/case-studies/unitedhealth-group-standardizes-on-verint-knowledge-management-enterprise-wide |
| 5.27 | Salesforce Knowledge Developer Guide, articles and data categories | https://developer.salesforce.com/docs/atlas.en-us.knowledge_dev.meta/knowledge_dev/knowledge_development_object_managing_articles.htm |
| 5.28 | Shelf Help, advanced scores in Content Intelligence | https://help.shelf.io/advanced-scores-in-content-intelligence-5983adf3 |
| 5.29 | Shelf contact center knowledge solution page | https://shelf.io/contact-center-knowledge-solution/ |
| 5.30 | CX Today, Gartner Magic Quadrant for CS-KMS 2026 rundown | https://cxtoday.com/gartner-magic-quadrant-customer-service-knowledge-management-2026 |

**Health insurer precedents (5)**

| # | Source | URL |
|---|---|---|
| 5.31 | Humana, Agent Assist built with Google Cloud (Feb 2026) | https://news.humana.com/news/articles/humana-redefines-the-member-experience-with-agent-assist-built-with-google-cloud (independent: https://www.fiercehealthcare.com/payers/humana-taps-google-cloud-new-agent-assist-ai-tool) |
| 5.32 | UnitedHealthcare, Avery AI companion (Mar 2026) | https://www.unitedhealthgroup.com/newsroom/2026/2026-03-26-uhc-introduces-ai-companion-empowering-people-with-simpler-navigation-personal-experience.html |
| 5.33 | Elevance Health, how AI helps improve the consumer experience | https://www.elevancehealth.com/our-approach-to-health/digitally-enabled-healthcare/how-ai-helps-improve-the-consumer-experience |
| 5.34 | Independence Blue Cross GenAI tool for customer service reps (Managed Healthcare Executive, Jun 2025) | https://www.managedhealthcareexecutive.com/view/ibx-joins-growing-ai-wave-with-genai-tool-to-boost-customer-service-and-member-trust |
| 5.35 | Oscar Health, "Building a Superagent" | https://oscar-ai.squarespace.com/blog/building-a-superagent-how-were-using-ai-to-explain-healthcare-faster |

LG5 has 36 approved sources. Under the plan, more than 30 means two subagents: Palantir (5.1 to 5.14, plus 5.36) and everything else (5.15 to 5.35).

---

## Sign-off record (2026-11-02)

1. Company selection: approved.
2. LG4 at 13 sources: approved.
3. HDI and TSIA: dropped.
4. Palantir 5.13: the forum thread was too thin. Replaced with the AIP Document Intelligence docs, and GAO-21-600 added as 5.36 for HHS Protect.

## Sign-off record (2026-11-02, after first reading pass)

1. LG3 Stage 1 sources below 0.85 (3.11, 3.17, 3.18): keep.
2. 3.1 Moffatt v. Air Canada: user supplied the decision PDF, local-sources/moffatt-v-air-canada-2024-bccrt-149.pdf.
3. Re-read sources cut off by the fetch tool: agreed.
4. 2.4 HORIBA: user supplied the PDF, local-sources/rws-horiba-medical-case-study.pdf.
5. 2.10 Veeva MLR: user supplied the PDF, local-sources/veeva-promomats-next-gen-mlr-review.pdf (title "Next-gen MLR Review"), replacing the redirected page.
6. 2.11 Klick: user pasted the full article text, saved as local-sources/klick-from-checkpoint-to-input.md.
7. 2.12 FDA SPL (Stage 1 p1 0.64): keep.

## Sign-off record (2026-11-02, LG1 decisions)

1. 1.11 McKinsey: user supplied the PDF, local-sources/mckinsey-where-is-customer-care-in-2024.pdf.
2. 1.12 Gartner: skipped (paywalled; stays logged as COULD NOT ACCESS).
3. 1.9 NBER: SKIMMED is acceptable.
4. 1.10 Salesforce State of Service (Stage 1 p1 0.84): include.
5. 1.1 widened to the Evolve Loop and Content Health practice pages. Bounded set (11 pages, each page's own text only):
   - The Evolve Loop: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040
   - Practice 5, Content Health: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010
   - Technique 5.2, KCS Article State: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/030
   - Technique 5.5, Archiving Old Articles: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/044
   - Technique 5.6, Dealing With Legacy Data: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/045
   - Technique 5.9, Knowledge Domain Analysis: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/060
   - Technique 5.10, Content Health Indicators: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/065
   - Practice 6, Process Integration: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/020
   - Technique 6.3, Search Technology for KCS: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/020/040
   - Practice 7, Performance Assessment: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/030
   - Practice 8, Leadership and Communication: https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/040

## Sign-off record (2026-11-02, LG4 decisions)

1. 4.5 42 CFR 422.504 (Stage 1 p1 0.65) and the Humana CMP letter opened under 4.8 (p1 0.77): keep both.
2. 1.10 Salesforce State of Service: keep (confirmed again).
3. LG4 follow-up approved: open recent (2023 to 2026) CMP and sanction letters listed on the 4.8 enforcement index, to find cases about inaccurate or inconsistent member communications, marketing, or customer service. Boundary: open at most 12 letters. Each letter opened becomes an item 4.8.x.
4. Opus review of all judgment flags (LG1 to LG4) approved, to run after the follow-ups finish.

## Sign-off record (2026-11-02, 1.11)

1.11 McKinsey, "Where is customer care in 2024?" (Stage 1 p1 0.32): dropped by user decision. Its notes entry stays in notes-lg1.md for the record, but nothing from it may be used in synthesis or the report. The coverage table lists it as READ IN FULL, dropped by user decision.

## Sign-off record (2026-11-02, Opus review questions)

1. 1.13 Shelf: keep the casestudies.com listing only. Its figures are labeled vendor claims that could not be verified.
2. LG2 gaps (expiry, retirement, conflicts between approved versions, migration effort): accepted, reported as "not disclosed in the sources read". The LG5 Palantir reader should note anything on these topics, even adjacent or tangential (for example versioning, conflict resolution, lifecycle, migration in the Ontology docs).
3. Rx pricing disclaimer framing: read one current CMS memo or set of guidance first, then decide. LG5 is on hold until then.

## Added source (2026-11-02, Rx disclaimer framing question)

| # | Source | URL | Note |
|---|---|---|---|
| 4.14 | CMS HPMS memo, "2026 Part C and Part D Call Center Monitoring" (9 pages, PDF created 2025-12-01) | https://24393978.fs1.hubspotusercontent-na1.net/hubfs/24393978/2026%20Part%20C%20and%20Part%20D%20Call%20Center%20Monitoring.pdf | Third-party-hosted copy. No cms.gov copy found. Saved as local-sources/cms-2026-part-c-d-call-center-monitoring.pdf. Read to settle Opus review question 3, on whether CMS guidance requires specific language on customer service and pharmacy calls. Candidates checked and rejected: "Expectations for Customer Service Call Handling" (2006, not current). |

## Added sources (2026-11-02, call center regulations)

| # | Source | URL | Note |
|---|---|---|---|
| 4.15 | 42 CFR 422.111, Disclosure requirements, paragraph (h) only | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-C/section-422.111 | MA call center requirements cited by 4.14 |
| 4.16 | 42 CFR 423.128, Dissemination of Part D plan information, paragraph (d) only | https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-C/section-423.128 | Part D call center requirements cited by 4.14 |

## Sign-off record (2026-11-02, framing and LG5 start)

1. Rx pricing disclaimer framing confirmed. The deck presents the disclaimer as wording the plan's Legal team requires, with 423.2267(e)(40) cited only as a similar case. It states that CMS call center rules and guidance name no required wording on customer service or pharmacy calls. It adds that 423.128(d)(1)(vi) and (d)(4) require the cost sharing and formulary information given to Part D callers to be accurate and timely.
2. LG5: start the Palantir reader only (5.1 to 5.14 and 5.36). The non-Palantir LG5 reader (5.15 to 5.35) stays on hold.

## Sign-off record (2026-11-02, LG5 remainder)

1. Start the non-Palantir LG5 reader (5.15 to 5.35).
2. After it completes, run an Opus review of all LG5 judgment flags (Palantir and non-Palantir).

## Sign-off record (2026-11-02, LG5 user-supplied text)

1. 5.18 Microsoft Tech Community, "Mitigate Oversharing to Govern Microsoft 365 Copilot and Agents" (Sep 2, 2025): the user pasted the full text, saved as local-sources/microsoft-mitigate-oversharing-copilot-agents.md.
2. 5.24 eGain release: the user confirmed it is a true 404. It stays COULD NOT ACCESS.
3. 5.31b Fierce Healthcare, "Humana taps Google Cloud for new Agent Assist AI tool" (Feb 3, 2026): the user pasted the full text, saved as local-sources/fierce-humana-agent-assist.md.
4. A follow-up reader adds 5.18 and 5.31b to notes-lg5-other.md after the LG5 Opus review finishes.

## Scoping table corrections (2026-11-02, after the LG5 Opus review)

These scoping-pass statements above came from search-result snippets and are not supported by the approved pages read. They stand corrected here. The synthesis and report must not rely on the uncorrected wording.

1. Salesforce Knowledge row: "Approval processes are documented." The approved page (5.27) has no approval content.
2. Shelf row: the unnamed Fortune 50 healthcare case and the PBM case appear on neither 5.28 nor 5.29.
3. Gemini Enterprise row: "an access-control setting that cannot be changed after a data store is created" is on neither 5.19 nor 5.20.
4. Coveo row and recommendation: "documents cited generative answers." Neither 5.21 page documents citations. Corrected wording: index-level permissions and grounded generative answers.
5. Coveo row: "a Humana case study is listed, with a headline only." The listing (5.22) has two paragraphs and a figure. The Manulife mention is unverified.
6. eGain row: the "leading US health insurer" release (5.24) is a confirmed 404, so it is unverified. The Allegiance (Cigna) 2022 mention has no approved source.
7. Verint row: the BCBS Louisiana and Humana case mentions have no approved source.
8. Microsoft 365 Copilot row: "documented failure mode" overstates the landing page (5.17), which gives no example or incident. Microsoft's own description of oversharing patterns comes from 5.18 (user-supplied text).
9. Gemini Enterprise row: no approved source ties Humana's "Gemini Enterprise for CX" stack to the connector product described in 5.19 and 5.20.
10. 5.9 corpus entry: the FY2025 filing has no "healthcare" section. Healthcare passages were found by text search.
11. 5.11 corpus entry: "insurer, health line" is unverified, because the source could not be accessed.
12. Statements about companies not selected cite pages outside the corpus. They were not checked and must not be used as findings.

## Sign-off record (2026-11-02, LG5 review questions)

1. 5.12a NHS England evaluation page: the user pasted the text, saved as local-sources/nhs-england-fdp-evaluation.md. The user offered the full OSR statement and the Imperial evaluation plan PDF; they are not requested at this point.
2. 5.11 GNP Seguros Business Wire release (Jul 7, 2026): the user pasted the text, saved as local-sources/businesswire-palantir-gnp-seguros.md.
3. 5.36 GAO-21-600: moved out of the Palantir section. It is used only as a lesson on shared data definitions and reporting standards in a centralized government health data system. It is not evidence about Palantir.
4. 5.16 Glean healthcare page (Stage 1 p1 0.75): keep.
5. 5.17 Microsoft blueprint: keep the landing page only; the linked PDF is not read.

## Sign-off record (2026-11-02, coverage checkpoint)

The user asked to begin step 5 after credits reset, which serves as sign-off on the coverage checkpoint. Step 5 (synthesis, the final-wording Jev re-check, and final-report.md) is scheduled to start at 4:15 AM Eastern on 2026-11-03.
