# Governed Knowledge and Search for a Medicare Advantage Contact Center: Research Report

> **Public copy:** this document refers to internal working files (such as the per-goal research notes) that are not included in this public copy of the repository.

Prepared 2026-11-03 from the notes files only (notes-lg1.md to notes-lg4.md, notes-lg5-palantir.md, notes-lg5-other.md), with the coverage manifest, the merged access-failure list, the quote verification report, and both judgment-flag reviews. References are numbered by source ID (for example [3.1]) and listed at the end with links. Each reference is marked READ IN FULL or SKIMMED there; the coverage table in section 6 gives the status, a proof quote and the Jev Stage 1 result for every source.

Labels used in the text:
- **Documented**: a regulation, enforcement letter, court or tribunal decision, government report, peer-reviewed or preprint research, independent press, or a vendor's own product documentation describing a mechanism.
- **Company-stated**: a vendor's or payer's press release, marketing page, case study or blog, including any outcome figure in it.
- **Inference**: my reading where the sources are silent or only imply something.

---

## 1. Executive summary

Knowledge bases decay mainly through process failures: findability problems, update burden, stale content, duplicates, approval bottlenecks, and copies held in separate silos. Each of these is documented in a practitioner survey and in named adopter case studies [1.8][1.5][1.7]. A failure like the one in the case also has a documented regulatory cost. CMS fined Aetna $1,000,000 in 2015 because wrong pharmacy-network data reached members through both its website and its call center representatives [4.9]. A tribunal held Air Canada liable when its chatbot contradicted the airline's own policy page [3.1].

Pre-generative-AI precedents for single-source, versioned content in regulated industries do exist:
- FDA Structured Product Labeling identifies a document by a stable set ID, a version number and an effective date [2.12];
- DITA content reuse renders one source element everywhere it is referenced [2.3];
- pharma claims libraries approve a claim once for reuse [2.9].

The precedents also show the limit. In an FDA-regulated firm, a pre-approved topic could not be reused automatically, because content "must get approved in context of the entire deliverable" and a topic's specifications may not apply to another product [2.6].

Research on retrieval-augmented generation explains why ungoverned retrieval is unsafe for verbatim content:
- models adopt incorrect retrieved content over 60% of the time even when they know the right answer [3.6];
- they hallucinate more often than they abstain when context is insufficient [3.10];
- commercial legal research tools built on curated corpora still hallucinated 17% to 33% of the time [3.3].

The vendors closest to the case are eGain and Verint, which market or describe a single governed knowledge layer for health plans (company-stated) [5.23][5.26]. No source documents how any vendor stores mandatory verbatim, finds every copy of it, or proves which version was in effect on a date. Palantir's documented controls attach to structured data, and its own documentation says its row and column read controls "do not extend to the model's output" [5.7a].

The biggest remaining gap is evidence. No source measures whether restricting answers to approved units, with abstention, reduces harmful answers in a regulated contact center. No source publishes a numeric launch gate that a regulated team actually used.

---

## 2. Findings by learning goal

### Learning Goal 1: Why knowledge bases rot, and how search logs fix it

**Q1. Documented causes of decay, and which sources measure them.**
- **The only survey measure:** a 2021 vendor-sponsored survey of 224 contact centre professionals ranked the top knowledge base challenges as follows [1.8]:
  - finding information quickly, 58.6%
  - updates being difficult and time-consuming, 37.0%
  - out-of-date information, 32.7%
  - duplicate information, 25.3%
  - only a small group able to make changes, 23.5%
- **Named adopters:**
  - Progress Software had a QA gate that released only 25 of every 100 solutions, despite a QA group of up to 10 people. Its "emphasis on volume knowledge capture had resulted in duplications and poorly documented solutions" (company-stated, 2006) [1.5].
  - ServiceNow describes knowledge captured "in email, intranet sites, notes, documents, and often just in their heads", regional silos, and "A multi-step approval process delayed content availability by weeks, and curation to remove outdated or duplicate content was an issue." (company-stated) [1.7].
- **Methodology view:** KCS says "Archiving old articles treats the symptoms of findability, not the cause" and that search technology "can not overcome deficiencies in our content" [1.1].
- **Healthcare (company-stated, unnamed customer, no baseline):** Shelf says outdated and inaccurate documentation put a Fortune 50 healthcare company in breach of its first contact resolution SLA, and caused its agent assist tool "to provide bad answers, leading to a loss of trust" [1.13].
- **Channel-specific copies:** no LG1 source measures them as a separate cause. The Aetna penalty shows the same wrong data reaching two channels [4.9].

**Q2. What KCS prescribes, and what adopters report.**
- **Capture in the workflow.** KCS says knowledge "is captured and structured during the request-response interaction", and "The act of searching captures the request and the environment in which the issue occurs" [1.1].
- **Search failures as demand.** KCS lists "Search analytics - looking for "no match found" queries" as a source of search weaknesses and routes a gap to a Knowledge Domain Expert. Knowledge Domain Analysis has four outputs:
  - findability issues
  - content gaps
  - content overlaps ("consolidating duplicate articles, identifying the best or preferred resolution among many proposed resolutions")
  - an archiving strategy [1.1]
- **Ownership is spread across roles.** Article quality is "the responsibility of everyone who interacts with the knowledge base". Knowledge Domain Experts look after a domain. Only designated people may create or modify articles carrying the "Compliance Based" attribute [1.1].
- **Review is driven by demand.** KCS says "If we are reviewing articles in absence of demand, we are not doing KCS", and that policy or regulatory content has "no tolerance for variability" [1.1]. I read these two statements as a tension: legal verbatim needs review when the law or policy changes, whether or not anyone is using the article (inference).
- **Named adopter results:**
  - Progress's Knowledge Domain Manager monitored "search strings, solutions found and considered, and the case log", and acted as "the arbiter when solutions collide". Progress reports a reuse-to-creation ratio of eight or nine to one (company-stated) [1.5].
  - Omgeo, a financial services firm, clustered articles by cause and resolution starting in 2011. The first analysis took about 40 hours, and its first output was "data but not information" for the development team (company-stated) [1.6].
  - ServiceNow reports cases with an attached article "solved 52% faster" and an 87% rise in attach rate (company-stated; this is a correlation, not a controlled comparison) [1.7].
- **Timeline:** KCS says results "take two to three years to realize" [1.3].

**Q3. Content health metrics, and published benchmarks.**
- **Named metrics:** KCS names currency trends, article life cycle, time to publish, the Content Standard Checklist, link rate, link accuracy, uniqueness, and "Percentage of searches with results" [1.2][1.3][1.1].
- **Targets the Consortium states, without a dataset:**
  - link rates above 60% and link accuracy above 90% [1.1];
  - the "Ideal = 85% new" ratio of known to new issues [1.2].
  - Measurement Matters labels its own numbers "an example of the scope and dynamics of the KCS impact" [1.3].
- **Not disclosed in the sources read:** any adopter benchmark for staleness rate, duplicate rate, or zero-result search rate.
- **Measurement failure mode:** the Consortium renamed its Article Quality Index because organizations "put all of their focus on the number" [1.4]. It also warns "DO NOT PUT GOALS ON ACTIVITIES!" [1.2].

**Q4. Evidence linking knowledge quality to outcomes.**
- **Strongest evidence, AI assistance rather than knowledge governance:** a staggered rollout to 5,179 support agents of an AI assistant that included links to internal knowledge base documentation [1.9; skimmed] found:
  - 14% more issues resolved per hour, and 34% for novice and low-skilled workers;
  - chats 3.8 minutes shorter (9%);
  - a 1.3 percentage point gain in resolution rate on an 82% baseline, and no meaningful change in net promoter score;
  - agents with two months of tenure and AI access performed as well as or better than untreated agents with more than six months.

  The paper has no compliance or answer-accuracy measure.
- **Vendor figures:** knowledge-quality outcomes come only from vendors (company-stated):
  - first contact resolution "over 95%" after content cleanup [1.13];
  - "52% faster" solves for cases with attached articles [1.7];
  - an expected 20% fall in service costs and resolution times among AI agent users [1.10].
- **Compliance link:** this comes from LG4. CMS penalized inaccurate information given by call center representatives [4.9].

### Learning Goal 2: Single-source content in regulated industries

**Q1. How component content defines a unit, versions it, and propagates change.**
- **DITA:** reuse is a reference. "the referencing element acts as a placeholder for the referenced element" and "the content of the referenced element is rendered in place of the referencing element." [2.3]. Reuse works by pull or push, and processors check that the reused content is valid in each new context [2.2]. A reference can target an element in a topic or map, or a whole topic or map. "it is not possible to push a range of elements." [2.3]
- **FDA Structured Product Labeling** gives each document three fixed elements:
  - a set ID, which "remains constant through all versions/revisions of the document";
  - a version number, an increasing integer;
  - an effective time in yyyymmdd format.

  A reference to a core document "remains to the latest core-document with the same setId" [2.12].
- **Taken together:** this is a regulator-grade model for proving which version was current on a date (inference: it maps directly onto the case).

**Q2. How pharma governs approved language.**
- **Veeva PromoMats** (company-stated):
  - It offers "a library of pre-approved, channel-agnostic content modules", with section cards for Claims, Reusable Text and Images. "Reviewers can now see when content is pre-approved" [2.7].
  - "Claims and reference anchors get approved once as a claim record accessible to all." [2.9]
  - Veeva claims a 57% cut in review cycle time and 55% less time in review meetings for "centralized claims management and optimal MLR workflows", with no dataset named [2.9].
  - Veeva says auto-linking removes 90% of claims-linking work, and that pre-review adds five to 150 days per asset [2.10].
- **Adopter sign-off stays human:**
  - Astellas: "Ensuring compliance with FDA requirements remains a key responsibility of our MLR teams, which AI alone cannot handle."
  - Sanofi: "human oversight is crucial to maintain accuracy and compliance." [2.10]
- **Klick, an agency** (company-stated, broad definition of rejection, unnamed client): it reports a 16-day shorter average MLR cycle and 12% more first-round approvals. The report doesn't say whether the 12% is relative or in percentage points. These came from putting "Previously approved claims, with their supporting evidence and approval conditions" in front of authors while drafting [2.11].
- **Adoption claim:** Veeva says eight of the top 10 biopharmas use PromoMats for modular content (company-stated) [2.8].

**Q3. Governance roles and workflows, and where they broke down.**
- **Carestream**, an FDA-regulated device maker (practitioner interview):
  - up to 12 approver roles, including Health & Safety, Regulatory and Compliance;
  - "When audited, we must be able to show traceability from the deployed content back to the source in our CMS.";
  - validating a content management system "can take several weeks to months";
  - asked whether a "pre-approved" topic can be reused automatically, the interviewee answered no, "because the content must get approved in context of the entire deliverable". In the example given, a reused topic listed specifications that did not all apply to the other product [2.6].
- **Progress Software:** named a Knowledge Domain Manager to arbitrate colliding solutions [1.5].
- **Not disclosed in the sources read:** expiry, retirement, or resolution of a conflict between two approved versions.

**Q4. What adopters underestimated.**
- **Migration.** HORIBA Medical considered converting legacy material automatically "but decided it would be more strategic to start writing structured content from scratch". Its seven writers built 4,500 objects over two years, supporting more than 13,500 documents (company-stated) [2.4]. KCS says "We have never seen a mass migration of legacy content work in a KCS implementation." [1.1]
- **Training.** Carestream trained writers from a year before implementation onward [2.6].
- **Granularity and applicability.** At Carestream, approval in the context of a whole deliverable meant pre-approved topics still needed review when reused, because applicability differed by product [2.6].
- **Effort figures:** not disclosed in the sources read.

### Learning Goal 3: Why naive retrieval fails in regulated settings, and what works

**Q1. Documented incidents and their stated causes.**
- **Moffatt v. Air Canada (2024).** The chatbot said a bereavement fare could be claimed within 90 days after travel, while the linked policy page said it could not. The tribunal held: "It should be obvious to Air Canada that it is responsible for all the information on its website. It makes no difference whether the information comes from a static page or a chatbot." It awarded $812.02 in total [3.1].

  The decision gives no technical cause: Air Canada "did not provide any information about the nature of its chatbot" [3.1]. Any retrieval explanation for this case is inference. The tribunal is Canadian and its decision does not bind US courts.
- **New York City's MyCity chatbot**, built on Microsoft Azure AI services over "more than 2,000 NYC Business web pages", told business owners things that contradict the law. It also answered the same housing-voucher question differently for different askers. No root cause was stated [3.2].
- **Commercial legal research tools** with curated corpora hallucinated 17% to 33% of the time [3.3].
  - Accuracy was 65% for Lexis+ AI, 41% to 42% for Westlaw AI-Assisted Research, and 19% to 20% for Ask Practical Law AI. The paper states each of the last two figures differently in two places.
  - The authors say "Many failures in the three systems stem from poor retrieval", including citing documents that don't legally apply.
  - Westlaw sometimes stated propositions drawn from overruled cases without citing them. The authors' hypothesis is that citations are added in a second pass, with red-flagged cases suppressed.

**Q2. RAG failure modes in current published work.**
- **Conflicting or duplicate sources:**
  - models adopt incorrect retrieved content "overriding their own correct prior knowledge over 60% of the time", and subtle errors are adopted more readily than obvious ones [3.6];
  - failure point FP4 covers context with "too much noise or contradicting information" [3.4].
- **Stale content:** "Legal documents often contain outdated information" [3.3].
- **Volume in context:**
  - performance is highest when relevant information sits at the start or end of the context;
  - with 20 or 30 documents, worst-case accuracy fell below the closed-book baseline;
  - "model performance saturates long before retriever recall saturates" [3.7].
- **Citation without support:**
  - "even the best models lack complete citation support 50% of the time" on one dataset [3.8];
  - in generative search engines, 51.5% of sentences were fully supported by their citations and 74.5% of citations supported their sentence. Citation precision was inversely correlated with how useful users judged the answers [3.9].
- **Failure to abstain:**
  - the highest negative-rejection rates were 45% (English) and 43.33% (Chinese) for 2023 models [3.5];
  - "models tend to hallucinate more than they abstain" [3.10].
- **Chunking:** semantic chunking's cost was "not justified by consistent performance gains" over fixed-size chunks [3.13]. No source tests whether chunking splits required legal language (not disclosed in the sources read).

**Q3. Techniques with measured evidence.**
- **Hybrid retrieval and reranking** (vendor-published, non-regulated corpora): contextual embeddings plus contextual BM25 cut top-20 retrieval failure by 49% (5.7% to 2.9%), and adding a reranker cut it by 67% (to 1.9%) [3.12]. Reranking also raised citation recall from 73.6 to 84.8 on one benchmark [3.8].
- **Abstention gates:** combining a sufficient-context label with model confidence raised the correct share of answers given by 2 to 10 percentage points, on open-domain QA [3.10]. The abstention survey warns:
  - "neither probability-based measures nor verbalized confidence may be well-calibrated";
  - tuning for abstention can cause over-abstention;
  - an abstention should prompt a follow-up step [3.11].
- **Calibration:** a calibrated token-probability correction raised GPT-4o accuracy on conflicting evidence from 0.615 to 0.754 [3.6].
- **Curated corpus alone:** retrieval over a curated corpus did not prevent hallucination in the legal tools [3.3]. No source measures retrieval restricted to approved units.
- **Extractive answers for exact language:** not measured directly. Using the top retrieved passage as the answer gave "almost perfect citation quality" at much lower fluency and correctness [3.8]. Oscar says its benefit-document agent "extracts answers exclusively from these official documents, providing direct citations" (company-stated) [5.35].

**Q4. How practitioners evaluate, and what launch gate regulated teams use.**
- **Standard metrics:**
  - RAGAS defines faithfulness, answer relevance and context relevance. Its agreement with human raters was 0.95, 0.78 and 0.70 on a 50-page set [3.14].
  - ARES needs a human-labeled set of "approximately 150 annotated datapoints or more" and was about 59 to 60 points better than RAGAS on context relevance [3.15].
  - ALCE measures citation recall and precision. The metric itself agreed with human labels 85.1% (recall) and 77.6% (precision) of the time [3.8].
  - FACTS Grounding uses three judge models to limit self-preference, since judges rated their own outputs about 3.23% higher [3.16].
- **Guidance:** NIST advises verifying "sources and citations in GAI system outputs during pre-deployment risk measurement and ongoing monitoring activities". It also advises sharing pre-deployment results with whoever holds release approval authority, and warns against extrapolating from anecdotal tests [3.17; skimmed]. Barnett et al. say validation is only feasible during operation [3.4].
- **The only payer launch gate disclosed** is Oscar's (company-stated) [5.35]:
  - a 90% groundedness threshold, set from a human care-guide benchmark of 90% groundedness and 62% completeness;
  - a later batch reaching 96% groundedness.
- **A numeric gate used by a regulated team:** not disclosed in any other source read.

**Q5. How permissions are enforced in retrieval, and leakage risks.**
- **Pre-filter versus post-filter:** none of the sources read states which is used. That covers OWASP, Azure, Glean, Gemini Enterprise, Coveo and Palantir.
- **Azure's security filter pattern** applies a filter built from the caller's groups "to every query". It warns that the principal "is just a string" and that the pattern itself does no authentication [3.19].
- **Coveo's worked example:** the index "Retrieves all items matching the query" and then filters out denied items. Where permission information is missing, it "applies the strictest option" [5.21a][5.21b].
- **Documented leakage risk:** in shared vector stores, embeddings from one group can be retrieved for another group's queries. OWASP prescribes permission-aware stores, partitioning, and "detailed immutable logs of retrieval activities" [3.18].
- **Output is not covered by read controls:** Palantir documents that row and column read controls "do not extend to the model's output or any Ontology edits it composes" [5.7a].

### Learning Goal 4: What Medicare requires

**Q1. Required disclaimers, standardized language, and content delivered on calls.**
- **Standardized content** "must be used in the form and manner provided by CMS", without alteration except listed edits such as filling variable fields [4.2]. The Part D text is parallel, with the accompanying-language rule at 423.2267(b)(3) [4.3].
- **Model content** "Must accurately convey the vital information", but need not be used verbatim [4.2].
- **Spoken requirements in the text** are all tied to telephonic enrollment, sales calls, or a specific notice [4.2][4.3]:
  - reviewing the pre-enrollment checklist before a telephonic enrollment;
  - telling the beneficiary where to find the Summary of Benefits and the Star Ratings document;
  - a telephonic provider termination notice;
  - the third-party marketing organization (TPMO) disclaimer, "Verbally conveyed during sales calls prior to the discussion of any benefits."
- **The closest analog to the case's Rx pricing disclaimer** is the Part D standardized statement on limited access to preferred cost-sharing pharmacies. It applies to "all materials mentioning preferred pharmacies", and its text says nothing about spoken statements [4.3].
- **Call center guidance and rules** name no required wording for customer service or pharmacy calls [4.14][4.15][4.16]. Under 423.128(d)(1)(vi) and (d)(4), Part D call centers must give callers enrollee cost-sharing and formulary information. (d)(4) calls that information "complete, accurate, timely, clinically appropriate, patient-specific" [4.16]. Whether those adjectives bind what a representative says aloud is my reading of the cross-reference.

**Q2. Customer service and pharmacy calls versus sales calls, and the communications and marketing line.**
- **The definitions:** "Marketing is a subset of communications", and requires both a plan-selection or retention intent and benefits, cost or ranking content. CMS judges intent from objective context, "not limited to the MA organization's stated intent" [4.1]. These definitions are unchanged since May 2022 [4.7].
- **Mid-call transition:** the 2022 Marketing Guidelines say a customer service call moves "from communications to marketing" when the enrollee asks about other plan options. The plan must signal the change and obtain consent before a transfer. This is 2022 guidance, and no approved source states it is current [4.6].
- **TPMO disclaimer:** the CY2027 rule ties it to the "discussion of benefits" and says "the mere mention of a benefit" does not count [4.7].
- **CMS testing of call centers** [4.12][4.14]:
  - It secret-shops the accuracy of plan information given by customer service representatives, on prospective-beneficiary lines.
  - It tests current-enrollee and pharmacy help desk lines for hold time (2 minutes or less) and disconnect rate (5% or less) only.
  - In 2022 it said it asks no benefit questions on those lines.

**Q3. Recordkeeping, call recording, retention, and proof of the version in effect.**
- **Marketing and sales calls under TPMO contracts:** they "must be recorded and retained in their entirety for a minimum period of 6 years", in audio for the first 3 years [4.4]. The CY2027 rule set this, replacing an expected 10 years. Enrollment records stay at 10 years [4.7].
- **General contract records:** kept for 10 years, with CMS audit access [4.5].
- **Not in any approved source:**
  - a requirement to record customer service calls;
  - a requirement to prove which version of required language was in use on a given date.
- **Version-control mechanisms that do appear,** all in the 2022 Marketing Guidelines [4.6]:
  - the HPMS Marketing Module as "the primary system of record" for submitted materials, including scripts;
  - replaced materials marked "no longer in use" and resubmitted with a new SMID;
  - a last-update date shown next to website materials.

**Q4. Enforcement actions citing inaccurate or inconsistent communications.**
- **Aetna (2015), $1,000,000:** 6,887 non-network pharmacies were shown as in-network "on its website and through its call center customer service representatives". 2,750 complaints (73% of Aetna's complaints) were marketing complaints that beneficiaries had been misled. CMS granted a special enrollment period. The basis was the failure "to disseminate clear and accurate information" under 423.128(a)(2) [4.9].
- **InnovaCare (2013), $49,710:** its combined Annual Notice of Change and Evidence of Coverage "incorrectly stated that beneficiaries do not have a coverage gap", affecting 4,971 members. CMS noted "Fifteen (15) sponsors have been assessed civil money penalties for inaccurate documents since 2010." [4.10]
- **Recent letters:** I checked 12 letters from 2023 to 2026, plus a 2025 Humana penalty for claims processing. None cites inaccurate member communications [4.8]. This is a sample chosen by size and sanction type, so it does not show that no recent case exists. Two enrollment suspensions direct that marketing and communications "must accurately reflect" closed enrollment, with no finding that anything was inaccurate [4.8.9][4.8.10].
- **CMS's 2025 audit report** names this finding: "Required notice updates, such as the new 65-day appeal timeframe, were not implemented consistently across multiple systems and delegated entities." It advises sponsors to "Test denial notices or messaging across platforms." [4.11]

**Q5. CMS or HHS guidance on AI in member communications or customer service.**
- **None found in the bounded source set.**
  - The 2024 CMS FAQ covers AI in coverage determinations only, and puts responsibility on the plan [4.13a; skimmed; quotes not verified by the automated check].
  - The marketing and communications sections of the April 2026 rule do not mention AI [4.7].
  - The 2026 call center memo mentions IVR only [4.14].
  - The HHS AI strategy page could not be accessed [4.13b].
- **Scope of the finding:** the sources read say nothing on this. That does not show that no such guidance exists.

### Learning Goal 5: Who has tried this, and what transfers

Section 3 compares every company. The notes below cover what matters most for each.

- **Palantir**
  - *Mechanisms (vendor documentation):*
    - The Ontology is "an operational layer for the organization" over "datasets, virtual tables, and models" [5.1].
    - "Markings are a mandatory control" that "travel with the data", inherited along file hierarchy and dataset dependencies [5.4].
    - Actions give one validated write path "across all user-facing applications" [5.3].
    - Logic can stage AI edits "for human review" [5.7a], and AIP Evals compares test cases "against previous versions of your function" [5.8].
  - *Unstructured documents:* the one page on them, Document Intelligence, stops at extraction to Markdown with optional chunking [5.13].
  - *Deployments:*
    - The only insurer deployment read, GNP Seguros, covers claims, risk and underwriting data. It mentions no policy, script or regulatory text (company-stated) [5.11].
    - Independent reporting on the NHS Federated Data Platform quotes Leeds Teaching Hospitals: "we believe we would lose functionality rather than gain it". It also reports that 45 of 215 hospital trusts were actively using the platform by the end of 2024 [5.12b]. NHS England's own page reports no benefit figure [5.12a].
  - *Criticism:* a competitor argues "Permissions cannot be exported between different data backbones" [5.14].
  - *Classification:* partial analog for structured-data controls, and a contrast case for governed prose.
- **Enterprise search**
  - *Glean* documents that a document a user cannot open "can't be used as context, returned as a search result, or surfaced as a citation" [5.15].
  - *Microsoft* says Copilot generates content from what each user may access, so "gaps in governance ... become amplified", and that "Most internal oversharing stems from configuration issues" (company-stated) [5.18].
  - *Gemini Enterprise* syncs identity separately from content: identity as often as every 30 minutes, content every 3 hours by default. Incremental syncs do not capture deletions [5.19].
  - *Coveo* stores permissions in the index and denies by default [5.21a][5.21b].
  - *Lesson:* all four govern who can read. None governs which content is approved.
- **Contact center knowledge (company-stated except Salesforce and Shelf documentation)**
  - *eGain* markets "One versioned, audited knowledge layer that every agent, AI system, and quality team draws from" for health plans [5.23].
  - *Verint* reports UnitedHealth Group runs "over 80,000 total knowledge articles across more than 40,000 users and 50 distinct roles and functions" on one authoring and publishing platform. The program started after a 2018 outage forced 40,000 return calls and threatened UHG's Star Ratings [5.26].
  - *Salesforce* documents a Draft, Online and Archived lifecycle with version IDs, and category-based access [5.27].
  - *Shelf* documents detection of exact duplicates, identical sections, 99%-similar near-duplicates, and contradictions between Q&A pairs. It publishes no accuracy figures [5.28].
  - *Gartner's first quadrant for this category* names eGain, Salesforce and Shelf as Leaders (reported by CX Today) [5.30].
- **Health insurer precedents (all company-stated)**
  - *Humana* runs Agent Assist for "more than 20,000 member advocates handling up to 80 million calls annually", with a "human in the loop", started in October 2025. Independent trade press restates the announcement and adds no corroboration [5.31a][5.31b].
  - *UnitedHealthcare's Avery* reaches 160,000 Medicare Advantage members and hands off to an advocate with "a full synopsis" [5.32].
  - *Independence Blue Cross* piloted a rep-facing tool with more than 40 reps, who validate answers against the CRM [5.34].
  - *Elevance's* claim tool works from claims data [5.33].
  - *Oscar* discloses the most: extractive citation from official plan documents, confidence-based escalation to a human, and a 90% groundedness gate [5.35].
  - *Gap:* none discloses how the content its tool surfaces is approved.

### Reconciliation notes (assumptions and tradeoffs)
- **Figures stated two ways in one source** are reported as a range citing both locations: Westlaw 41% to 42%, ARES 59 to 60 points, NBER adherence 35% to 38% [3.3][3.15][1.9]. The ARES figure is its gain over RAGAS on context relevance. The GE Healthcare saving is a single saving stated as both 30% and one-third [2.5].
- **The disclaimer framing follows the user's decision.** The case's Rx pricing disclaimer is presented as wording the plan's Legal team requires, with 423.2267(e)(40) cited only as an analog [4.3].
- **No single account is promoted to a pattern.** Air Canada and MyCity are two incidents with no documented technical cause. The case for governed units rests on the measured research in LG3 together with the enforcement record in LG4.
- **Palantir's role in HHS Protect** is not established by any source read, so the report makes no claim about it. The GAO audit is used only as a lesson on shared data definitions [5.36].

---

## 3. Who tried this: comparison table

D = documented (product documentation, regulation, research, independent press), CS = company-stated, NF = not found in the sources read.

| Company or category | Content type | Single source of truth | Permissions | Citation or lineage | Human approval | Regulated deployments | Documented limitations | What transfers |
|---|---|---|---|---|---|---|---|---|
| Palantir (partial analog for structured-data controls; contrast case for prose) | Structured operational data; PDF extraction to Markdown (D) [5.1][5.13] | Shared property definitions and one action write path (D) [5.2][5.3] | Mandatory markings inherited downstream; roles (D) [5.4][5.2] | Dataset lineage only (D) [5.6]; answer citation NF | AI edits staged for human review (D) [5.7a] | GNP Seguros, operational data (CS) [5.11]; NHS platform (D, independent press) [5.12b] | Read controls do not extend to model output (D) [5.7a]; trust-level doubts (D) [5.12b]; lock-in (critique) [5.14] | Marking propagation, staged review, test-case evals; prose governance NF |
| Glean (contrast case; partial analog for permission mirroring) | Any crawled enterprise content (D) [5.15] | NF | ACLs mirrored at crawl and evaluated at query time (D) [5.15] | Citations limited to documents the user can open (D) [5.15] | Agent write actions only (D) [5.15] | Payer marketing, no customer named (CS) [5.16] | Governs access; approval NF | Citation scoped to readable sources |
| Microsoft 365 Copilot (contrast case) | Microsoft 365 content (D) [5.17] | NF | Inherits user permissions (CS) [5.18] | NF | NF | NF | Oversharing amplified by governance gaps (CS) [5.18] | Pre-launch permission cleanup; label-based blocking |
| Google Gemini Enterprise (partial analog for ACL and identity mapping) | Connected third-party sources (D) [5.19] | NF | ACL per document, flattened identity mapping (D) [5.20] | NF | NF | Humana runs Gemini Enterprise for CX, a separate product (CS) [5.31a] | Sync lag; deletions missed by incremental sync (D) [5.19] | Identity mapping before content load |
| Coveo (partial analog for scoped, grounded retrieval) | Indexed enterprise content (D) [5.21a][5.21b] | NF | Permissions stored in index, default deny (D) [5.21a][5.21b] | Grounded answers (D); citation NF [5.21a][5.21b] | NF | Humana website and finder search (CS) [5.22] | Permission changes need reindex (D) [5.21a][5.21b] | Default deny when permissions are unknown |
| eGain (direct analog, company-stated only) | Health plan knowledge (CS) [5.23] | "One versioned, audited knowledge layer" (CS) [5.23] | NF | "auditable down to the source" (CS) [5.23] | "versioned, approved" (CS) [5.23] | Healthfirst testimonial (CS) [5.23] | Verbatim handling NF | Product pattern matches the case; verify in a demo |
| Verint (direct analog, company-stated only) | Knowledge articles (CS) [5.26] | One authoring and publishing platform, store-once (CS) [5.26] | Segmentation by role and user group (CS) [5.26] | NF | Authors approve and publish (CS) [5.26] | UnitedHealth Group, 80,000+ articles (CS) [5.26] | Outcomes Verint-published only | Center of excellence and role segmentation at payer scale |
| Salesforce Knowledge (partial analog for version and lifecycle) | Articles (D) [5.27] | One parent article, versions replace each other (D) [5.27] | Data categories and role visibility (D) [5.27] | Version IDs (D) [5.27] | NF on page read | NF | Approval workflow NF on page read | Draft, Online, Archived states; stable parent ID |
| Shelf (partial analog for duplicate and conflict detection) | Knowledge content (D) [5.28] | NF | NF | NF | NF | Unnamed Fortune 50 healthcare (CS) [1.13] | No accuracy figures (D) [5.28] | Duplicate, near-duplicate and contradiction checks |
| Health insurer precedents (Humana, UnitedHealthcare, Elevance, Independence Blue Cross, Oscar) | Benefits, claims and plan documents (CS) [5.31a][5.32][5.33][5.34][5.35] | NF except Oscar's plan-variant document selection (CS) [5.35] | NF | Oscar extractive citations (CS) [5.35] | Human in the loop (CS) [5.31a][5.32]; rep validates against CRM (CS) [5.34] | All are payers; Humana and UnitedHealthcare include Medicare Advantage (CS) | Results NF except Oscar groundedness (CS) and UnitedHealthcare deflection (CS) | Escalation with synopsis; groundedness gate; extractive citation |

---

## 4. Implications for the design

**Unit granularity and schema.**
- **What the unit is:** the smallest statement that can be approved on its own, together with the contexts it is approved for. Claims approved once are reused everywhere [2.9], but Carestream shows that reuse outside the approved context needs review, because applicability changes by product [2.6]. Oscar selects plan-specific document variants for each member (company-stated) [5.35].
- **Identity and versioning:** give each unit a constant ID, an increasing version number and an effective date, as in FDA SPL [2.12]. Render it by reference so one edit reaches every channel, as DITA does [2.3].
- **Schema fields:**
  - unit ID, version and effective date;
  - content class: verbatim, policy, or experience. KCS separates compliance-based content, which has "no tolerance for variability", from experience-based content [1.1];
  - owner and approver roles [1.1][2.6];
  - applicability scope: the plans, products and channels the approval covers [2.6][5.35];
  - knowledge base scope, used for permissions;
  - lifecycle state: draft, approved, or archived [5.27][1.1];
  - source document and location;
  - the channels that use the unit.

**Extractive versus generated answers.**
- **Verbatim units:** return the approved text extractively and cite the unit. CMS standardized content allows no alteration beyond listed edits [4.2]. Models adopt wrong retrieved text over 60% of the time [3.6]. Generated citations are often unsupported [3.8][3.9].
- **Policy units:** a generated summary is acceptable if it cites the unit and displays the governing verbatim alongside it. That is a design choice resting on the same evidence (inference). Oscar's use of extractive citation for plan documents is the payer precedent (company-stated) [5.35].

**Abstention threshold.**
- **What the evidence gives:** no source supplies a threshold for this domain. Models abstain too rarely [3.5][3.10], and their confidence may be miscalibrated [3.11].
- **Recommended design:**
  - put the gate outside the model: answer only when an approved, in-scope unit clears a retrieval score set on the golden set;
  - otherwise say the question cannot be answered and log it to the gap backlog. That treats abstention as a trigger for follow-up [3.11] and as KCS demand data [1.1];
  - measure over-abstention as well, since tuning for abstention can cause it [3.11].
- **Expected gain:** a modest precision gain, 2 to 10 points on open-domain QA [3.10].

**Permission scoping approach.**
- **Where the check runs:** no source says whether to filter before or after retrieval. Apply the caller's knowledge base scope as a filter on every query, as in the Azure pattern [3.19], over a partitioned index of approved units [3.18].
- **Defaults:**
  - deny when scope is unknown, as Coveo does [5.21a][5.21b];
  - log every retrieval [3.18].
- **Carry scope to the answer:** an answer should inherit its unit's scope, because read-time controls do not protect output by themselves [5.7a].
- **Avoid mirrored permissions:** storing scope on the unit avoids the sync lag that comes with mirroring permissions [5.19] and the oversharing that comes with inheriting them [5.18].

**Content types that require a human approval gate.**
- **Gate these:**
  - CMS standardized and model content [4.2][4.3];
  - any statement of cost sharing or formulary status given to Part D callers, which must be accurate and timely [4.16];
  - any content that discusses benefits or other plans, which moves a call into marketing [4.6][4.7];
  - the Rx pricing disclaimer and similar wording Legal requires [4.3].
- **Lighter review:** experience-based tips can follow KCS reuse-as-review [1.1].
- **Release approval:** share pre-deployment test results with whoever holds release approval authority [3.17]. Pharma keeps final compliance sign-off human [2.10].

**How drift detection should work.**
- **Link units to sources:** each unit records its source document and location. When the source changes, flag the unit for its owner. Palantir's dataset staleness coloring is the closest documented analog [5.6].
- **Find existing copies at migration:** run duplicate and near-duplicate detection. Shelf's identical-section check would catch copied text. Its near-duplicate rule triggers at 99% similarity, and whether three slightly different disclaimer wordings would reach that is not stated [5.28].
- **Keep a human in the loop:** no source reports accuracy for automated duplicate, contradiction or drift detection, so every flag goes to human review.
- **Why it matters:** both the Aetna error [4.9] and the 2025 CMS audit finding on notice updates [4.11] were the same change failing to reach every system.

**Eval metrics to use as a launch gate.**
- **What no source provides:** a numeric gate used by a regulated team, other than Oscar's company-stated 90% groundedness [5.35]. The gates below are proposals.
- **Proposed gates:**
  - exact-match rate for verbatim units on the golden set (design choice: 100%);
  - citation recall and precision [3.8];
  - faithfulness [3.14];
  - correct-abstention rate on out-of-scope and unanswerable questions [3.10];
  - zero permission leaks on cross-scope test queries [3.18].
- **How to label and maintain it:**
  - build the golden set with roughly 150 or more human labels, as ARES suggests [3.15];
  - verify citations before deployment and keep monitoring after launch [3.17];
  - keep testing in operation [3.4].

**Order of search go-live relative to the knowledge it runs on.**
- **Knowledge first.** Build the governed units before search goes live, starting with the highest-risk verbatim. KCS says search "can not overcome deficiencies in our content" and that mass legacy migration has never worked [1.1]. HORIBA wrote new structured content instead of converting legacy material [2.4].
- **Search only approved units,** launched per knowledge base. Log failed searches as the authoring backlog [1.1][1.5].
- **Keep legacy documents out of the answer path.** KCS's practice of keeping old repositories read-only [1.1] fits the case's rule that search returns approved units only.

---

## 5. Cross-cutting forces

| Dimension | What is changing | Direction and speed | Reading |
|---|---|---|---|
| S | A tribunal held a company responsible for its chatbot's statements as for any web page [3.1]; users rate polished answers useful even when citations do not support them [3.9]. | Liability for AI answers is attaching to the operator; one tribunal decision so far, 2024. | Risk |
| T | Hybrid retrieval and reranking cut missed retrieval sharply in vendor tests [3.12]; models still follow wrong retrieved content and abstain too rarely [3.6][3.10]. | Retrieval quality is improving fast; faithfulness and abstention remain unsolved in 2024 and 2025 research. | Both |
| E-env | Nothing in the sources bears on this case (by design). | | |
| E-eco | UnitedHealth Group plans $1.6 billion of AI investment this year and runs more than 1,000 AI solutions (CS) [5.32]; Humana deployed agent assist to more than 20,000 advocates (CS) [5.31a]; Gartner published its first quadrant for this category in 2026 [5.30]. | Payer spending and vendor categorization are accelerating in 2025 and 2026. | Opportunity |
| P | The CY2027 rule changes marketing rules from October 1, 2026, including the TPMO disclaimer trigger and a 6-year call-recording retention period [4.7]; no CMS or HHS guidance on AI in member communications was found [4.13a][4.7][4.14]; recent penalties focus on cost sharing and claims [4.11]. | Rules on sales calls are being adjusted annually; AI-specific rules for communications are absent. | Both: freedom to design now, risk of later rules |

---

## 6. Coverage table

The complete coverage manifest from the checkpoint, with the proof-of-reading quote, takeaway, provenance and user decisions for every source, is in [coverage-manifest.md](coverage-manifest.md). The merged access-failure list is in [access-failures.md](access-failures.md), and quote verification results are in [quote-verification.md](quote-verification.md). The table below is the manifest's per-source rows, generated from that file.

### Learning Goal 1: Why knowledge bases rot, and how search logs fix it

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 1.1a | KCS v6 Practices Guide, Section 2 (landing page) | READ IN FULL | web | "In KCS, we want the knowledge workers to use the knowledge base as the first resource in seeking a resolution to an issue." | Same as 1.1b (the notes carry one takeaway for entry 1.1) | p1 0.93 / p2 0.57 | Split batch: Opus review split 1.1 into 1.1a and 1.1b. No figures may come from 1.1a (p2 below 0.85). |
| 1.1b | KCS v6 Practices Guide, widened set (11 Evolve Loop and Content Health pages) | READ IN FULL | web | "Search analytics - looking for "no match found" queries" | KCS prescribes capture during the interaction, uses "no match found" queries and self-service gaps as the demand signal routed to Knowledge Domain Experts, spreads content health ownership across collective ownership, KDEs, and designated owners for Compliance Based articles, and publishes only Consortium-stated figures with no benchmarks for staleness or gap rate. | p1 0.97 / p2 0.99 | Widened by user decision (LG1 sign-off) to a bounded set of 11 pages. Images and the Knowledge Domain Analysis Reference Guide not read. Audit source condensed (about 1,600 characters). One claim check at 0.38 was revised (see access-failures.md). |
| 1.2 | KCS v6 Practices Guide, Appendix C: Metrics Matrix | READ IN FULL | web | "DO NOT PUT GOALS ON ACTIVITIES!" | KCS lists staleness and life-cycle metrics but gives no gap-rate or duplicate-rate metric and publishes only one target (85% new). | p1 0.93 / p2 0.97 | Truncation: Jev context was a condensed excerpt of selected rows (about 1,750 characters). |
| 1.3 | KCS Measurement Matters v6 (landing page plus 4 child pages) | READ IN FULL | web | "The benefits of KCS are profound, but the results take two to three years to realize." | KCS Measurement Matters names the content health and self-service indicators but its numbers are labeled examples, and it states results take two to three years. | p1 0.85 / p2 0.99 | P1 exactly at threshold (passes). Numeric indicators are Consortium-labeled examples. Claim 4 at 0.81 was revised. |
| 1.4 | Article Quality Index is now Content Standard Checklist | READ IN FULL | web | "In practice, this meant that organizations put all of their focus on the number generated as an indication of the quality of their knowledge base." | The Consortium itself reports that a numeric article quality index was gamed as a target and was replaced with a coaching checklist. | p1 0.96 / p2 0.53 | No figures recorded (p2 below 0.85). |
| 1.5 | KCS case study: Progress Software | READ IN FULL | web | "Finally, the tool and its customizations caused error-inducing duplication." | Progress is a named, dated adopter showing that review bottlenecks and volume incentives caused duplication, and that search strings and abandoned solutions were used by a named owner role as a content backlog signal. | p1 0.98 / p2 0.99 | Company-stated, dated 2006. Claim 5 (reuse rate) scored 0.83, then 0.76, then 0.89 after rewording. |
| 1.6 | KCS case study: Omgeo (financial services), Evolve Loop | READ IN FULL | web | "Clusters of KCS articles of similar cause and resolution are indicators of improvement opportunities." | Omgeo shows Evolve Loop clustering of article data as a named financial services precedent, with effort figures (40 hours) but no quantified outcome. | p1 0.96 / p2 0.99 | Company-stated, dated 2013. |
| 1.7 | KCS case study: ServiceNow, Faster Time to Relief | READ IN FULL | web | "TSEs were solving the same issues over and over; more than 60% had been already solved but the resolutions were not captured in a findable, reusable way." | ServiceNow is a named but vendor-authored adopter that attributes pre-KCS decay to siloed capture, slow approvals, and uncurated duplicates, and reports 87% more article attachment and 52% faster solves (company-stated). | p1 0.98 / p2 0.99 | Vendor-authored; all outcome figures company-stated. |
| 1.8 | Call Centre Helper, "Finding Information Quickly Is the Biggest Challenge" (2021 survey, n=224) | READ IN FULL | web | "This article explores the answers of 224 contact centre professionals when we asked 'What Are the Greatest Challenges in Managing Your Knowledge Base?'" | A vendor-sponsored 2021 survey of 224 contact centre professionals ranks findability, update burden, stale content and duplicates as the top knowledge base problems. | p1 0.95 / p2 0.99 | Vendor-sponsored; underlying survey report not read. |
| 1.9 | Brynjolfsson, Li, Raymond, "Generative AI at Work," NBER w31161 | SKIMMED | web | "agents with two months of tenure and access to AI assistance perform as well as or better than agents with more than six months of tenure who do not have access." | The best independent outcome evidence in LG1 comes from an AI assistant study, not a knowledge governance study, and shows the largest handle-time and ramp gains for novices with no compliance or content-quality measure. | p1 0.94 / p2 0.99 | SKIMMED accepted by user decision (LG1 sign-off). Section 1, references and appendix tables not read line by line. Adherence stated two ways (35% and 38%); both recorded with locations. |
| 1.10 | Salesforce, State of Service, 7th edition (PDF) | READ IN FULL | web | "Service ops and leaders who use AI agents expect their service costs and case resolution times to decrease by an average of 20%." | This Salesforce vendor survey offers expectations (20% lower cost and resolution time) and no knowledge-quality evidence, so it adds little to LG1. | p1 0.84 / p2 0.99 | Below threshold (P1). Kept by user decision (LG1 sign-off, confirmed again in LG4 sign-off). Chart values not recoverable. |
| 1.11 | McKinsey, "Where is customer care in 2024?" | READ IN FULL, dropped by user decision | user-supplied copy (PDF) | "More than 80 percent of respondents are already investing in gen AI, or expect to do so in the coming months, with leaders highlighting a wide range of potential applications." | This McKinsey 2024 survey piece gives gen AI adoption and two unnamed company examples (125-minute to seconds resolution time, 20 percent chatbot gain) but says nothing about knowledge base quality, so it adds only company-stated context to LG1 Q4. | p1 0.32 / p2 0.99 | Dropped by user decision (sign-off 1.11). Entry stays in notes; nothing from it may be used in synthesis or the report. Exhibits 1 to 3 (charts) did not extract. |
| 1.12 | Gartner, Magic Quadrant for Customer Service KMS, abstract (2026) | COULD NOT ACCESS: HTTP 403, Cloudflare challenge (paywalled) | none (not read) | none | not read. | Not run (no content) | Skipped by user decision (LG1 sign-off). Contents not inferred. |
| 1.13 | Shelf case study, Fortune 50 healthcare ("60%+ content ROT"), casestudies.com listing | READ IN FULL (listing page only, by user decision) | web | "The customer, a fortune 50 healthcare leader, was in breach of its SLA for first contact resolution due to out-of-date and inaccurate documentation, known as content ROT." | Shelf (a vendor) says an unnamed Fortune 50 healthcare company fixed a first contact resolution SLA breach by removing stale content, but the listing gives no baseline, date, or method. | p1 0.96 / p2 0.99 | Listing only, by user decision (Opus review question 1). The shelf.io case study was not read. Figures are vendor claims that could not be verified. The headline "60%+" is not a recorded figure. |

---

### Learning Goal 2: Single-source content in regulated industries

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 2.1 | OASIS DITA 1.3, Part 0: Overview | READ IN FULL | web | "defines a set of document types for authoring and organizing topic-oriented information" | The overview page is front matter and gives only a one-line scope statement for DITA. | p1 0.31 / p2 0.64 | Below threshold (P1). Protected category (DITA), not deprioritized. Page is front matter only. |
| 2.2 | DITA 1.3 spec 2.4.2: Content reference (conref) | READ IN FULL | web | "The DITA conref attributes provide mechanisms for reusing content." | DITA defines reuse as a typed reference resolved by the processor at build time, with push as well as pull. | p1 0.62 / p2 0.20 | Below threshold (P1). Protected category, not deprioritized. |
| 2.3 | DITA 1.3 spec 2.4.2.1: Conref overview | READ IN FULL | web | "the referencing element acts as a placeholder for the referenced element" | Reuse in DITA is a placeholder resolved at render time, so one edit to the source element changes every rendering. | p1 0.55 / p2 0.11 | Below threshold (P1). Protected category, not deprioritized. Propagation reading is labeled inference in the notes. |
| 2.4 | RWS Tridion Docs, HORIBA Medical case study (PDF) | READ IN FULL | user-supplied copy (PDF) | "Information is now written once, validated once and translated once. This results in documentation being updated more often at a much lower cost." | A 2021 vendor case study says one medical-device documentation team halved translation spend and stopped re-reviewing reviewed content after moving to DITA in Tridion Docs, and it gives no reuse percentage (company-stated). | p1 0.95 / p2 0.99 | Original web access failed (empty page, HTTP 202); user supplied the PDF (LG2 sign-off). Truncation: excerpt trimmed to 1,316 characters from non-contiguous passages. |
| 2.5 | Bluestream, GE Healthcare DITA case study | READ IN FULL | web | "The reuse model allows last minute updates to be easily incorporated into multiple publications at once." | GE Healthcare's vendor case study states a localization cost saving of 30% (In Brief) or one-third (main text, attributed to the XDocs Localization module), with no detail on governance or migration (company-stated). | p1 0.98 / p2 0.99 | Company-stated. The 30% and one-third are one saving stated two ways. Raw HTML re-read in Opus review confirmed the passages. |
| 2.6 | DITAWriter, "DITA in the Healthcare Sector" (Carestream interview) | READ IN FULL | web | "When audited, we must be able to show traceability from the deployed content back to the source in our CMS." | In an FDA-regulated firm, approval attached to the whole deliverable, not the reusable topic, which limited how far pre-approved topics could be reused. | p1 0.98 / p2 0.98 | Single practitioner account, likely pre-2022 (year not given). The earlier 406 did not recur. Combined claim at 0.77 was split and re-run. |
| 2.7 | Veeva PromoMats 2024 Innovation Guide (PDF) | READ IN FULL | web | "Easily ensure all your promotional content is linked to the approved Content Modules." | Veeva's modular content separates pre-approved typed modules from the assets that use them so reviewers look only at what is not already approved (company-stated). | p1 0.88 / p2 0.06 | No figures recorded (p2 below 0.85). Copy read carries a 2026 copyright and January 2026 creation date although the URL is dated 2024. Truncation: excerpt trimmed under 2,000 characters. |
| 2.8 | Veeva, "Modular Content Powers Omnichannel Engagement at Speed and Scale" (2023 PDF) | READ IN FULL | web | "With eight of the top 10 biopharmas using Vault PromoMats for modular content, and over 20 emerging companies starting to set a foundation" | Veeva claims large reuse and approval-time gains from modular content, but only for unnamed customers and "early indicators" (company-stated). | p1 0.95 / p2 0.99 | The document is a press release, not a white paper. Figures company-stated, customers unnamed. |
| 2.9 | Veeva, "Optimize MLR Workflows Using a Central Claims Library" | READ IN FULL | web | "Claims and reference anchors get approved once as a claim record accessible to all." | Veeva states that, in its experience, organizations with centralized claims management and optimal MLR workflows saw a 57% review-cycle cut and 55% less time in review meetings, with no dataset named (company-stated). | p1 0.95 / p2 0.99 | Company-stated. Raw HTML re-read in Opus review changed the attribution of 57% and 55%. |
| 2.10 | Veeva MLR white paper supplied in place of the Astellas and Merck KGaA blog post | READ IN FULL | user-supplied copy (PDF) | "Ensuring compliance with FDA requirements remains a key responsibility of our MLR teams, which AI alone cannot handle." | Named pharma MLR leaders say final compliance sign-off stays human even as claims linking and tiered review are automated, and Veeva states approved modules are reusable across channels (company-stated). | p1 0.93 / p2 0.99 (earlier text: 0.95 / 0.99) | Original blog URL redirected. User supplied a PDF (LG2 sign-off) that is a different document: "Building the Future of MLR with AI: Fastest Path to Approved Content". The blog post was not obtained and Merck KGaA is not covered. Truncation: excerpt trimmed to 1,114 characters from non-contiguous passages. |
| 2.11 | Klick, "From Checkpoint to Input: A Different Model for MLR" | READ IN FULL | user-pasted text | "Regulatory thinking enters as a creative input rather than arriving as a correction once the work is done." | An agency states, from its own data and with a broad definition of rejection, that bringing regulatory input before drafting with approved claims in front of authors cut one unnamed client's average MLR cycle time by 16 days (company-stated). | p1 0.95 / p2 0.99 (earlier text: 0.95 / 1.00) | User pasted the full article (LG2 sign-off), replacing a partial fetch extraction. Klick-stated figures; unnamed client. Claim reworded from 0.78 to 0.87. Truncation: excerpt trimmed to 1,404 characters. |
| 2.12 | FDA, Structured Product Labeling Resources (landing page plus 2 linked FDA pages) | SKIMMED | web | "Value of version number is greater than the value of any previously submitted version for the same set id" | FDA SPL fixes a document's identity with a constant set ID and orders its versions with an increasing version number plus an effective date. | p1 0.64 / p2 0.31 | Below threshold (P1). Kept by user decision (LG2 sign-off). Only sections 2.1.3 and 2.1.11 of the 273-page Implementation Guide were read. No figures recorded. |

LG2 note: expiry, retirement, conflict between approved versions, and migration effort are not documented in any LG2 source. Accepted by user decision and reported as "not disclosed in the sources read".

---

### Learning Goal 3: Why naive retrieval fails in regulated settings, and what works

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 3.1 | Moffatt v. Air Canada, 2024 BCCRT 149 | READ IN FULL | user-supplied copy (PDF of the official decision) | "It should be obvious to Air Canada that it is responsible for all the information on its website. It makes no difference whether the information comes from a static page or a chatbot." | A tribunal held an airline liable for a chatbot answer that contradicted the airline's own policy page, rejecting the argument that the chatbot was a separate source of information. | p1 0.86 / p2 0.99 | Both web copies returned HTTP 403; user supplied the PDF (sign-off, first reading pass). P1 passes narrowly. The decision gives no technical cause. |
| 3.2 | The Markup, "NYC's AI Chatbot Tells Businesses to Break the Law" | READ IN FULL | web | "there are no restrictions on the amount of rent that you can charge a residential tenant." | Same question returned different answers across askers, and the page disclaimer was the city's main mitigation; the article does not state a technical root cause. | p1 0.94 / p2 0.95 | Truncation: Stage 1 excerpt was a condensed set of quotes. |
| 3.3 | Magesh et al., "Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools" | READ IN FULL | web | "Over 1 in 6 of our queries caused Lexis+ AI and Ask Practical Law AI to respond with misleading or false information." | Commercial RAG legal tools with curated corpora still hallucinated 17% to 33% of the time, with the authors attributing failures to naive retrieval, inapplicable authority and reasoning errors, and noting that standard RAG evaluations assume retrievable documents are true and applicable. | p1 0.97 / p2 0.99 | First read stopped at character 100000 of 169846 (SKIMMED); re-read to the end from the PDF in a follow-up (agreed at sign-off). Westlaw 41% and 42%, Practical Law 19% and 20% recorded with locations. |
| 3.4 | Barnett et al., "Seven Failure Points When Engineering a RAG System" | READ IN FULL | web | "The first fail case is when asking a question that cannot be answered from the available documents." | Failure to abstain on unanswerable questions (FP1), contradicting context (FP4), and retrieval misses (FP2, FP3) are the named failure modes, and the authors say evaluation must continue in operation. | p1 0.94 / p2 0.98 | Corpus size stated two ways in the source (4,017 and 15,000); both recorded. Claim 1 first run 0.27, re-run 0.97. |
| 3.5 | Chen et al., "Benchmarking LLMs in Retrieval-Augmented Generation" (RGB) | READ IN FULL | web | "The highest rejection rates for LLMs in English and Chinese were only 45% and 43.33%, respectively." | 2023-era models abstained on no-evidence questions less than half the time and degraded as noise in retrieved context rose, which supports an explicit abstention gate outside the model. | p1 0.91 / p2 0.99 | 2023 models. |
| 3.6 | Wu et al., "ClashEval" | READ IN FULL | web | "susceptible to adopting incorrect retrieved content, overriding their own correct prior knowledge over 60% of the time." | When a retrieved unit is plausible but wrong, models often follow it over their own correct knowledge, so near-duplicate conflicting legal wordings are the hard case. | p1 0.94 / p2 0.99 | Source's Tables 2 and 4 use different measures for GPT-4o; only audited figures recorded. |
| 3.7 | Liu et al., "Lost in the Middle" | READ IN FULL | web | "performance is often highest when relevant information occurs at the beginning or end of the input context" | Passing many near-duplicate chunks can make answers worse than passing none, which supports retrieving few curated units and reranking. | p1 0.97 / p2 0.99 | 2023 models. |
| 3.8 | Gao et al., "Enabling LLMs to Generate Text with Citations" (ALCE) | READ IN FULL | web | "even the best models lack complete citation support 50% of the time" | A citation can be present without supporting the claim, reranking measurably improved citation recall in this benchmark, and the automatic citation metric itself agrees with human labels only about 78% to 85% of the time. | p1 0.96 / p2 0.99 | First read stopped at character 100000 of 127613 (SKIMMED); re-read to the end from the PDF in a follow-up. |
| 3.9 | Liu, Zhang, Liang, "Evaluating Verifiability in Generative Search Engines" | READ IN FULL | web | "frequently contain unsupported statements and inaccurate citations." | Users rate polished answers as useful even when citations do not support them, so citation support must be tested and cannot be judged by reading the answer. | p1 0.97 / p2 0.99 | |
| 3.10 | Joren et al., "Sufficient Context" | READ IN FULL | web | "models tend to hallucinate more than they abstain" | Abstention gated on a sufficiency check plus confidence gave a measured but modest precision gain (2 to 10 points), on open-domain QA and not on legal or policy text. | p1 0.92 / p2 0.99 | |
| 3.11 | Wen et al., "Know Your Limits: A Survey of Abstention in LLMs" | READ IN FULL | web | "We define abstention as the refusal to answer a query." | Survey caution that confidence thresholds can be miscalibrated, that tuning for abstention risks over-refusal, and that an abstention should lead to a follow-up step; this is a taxonomy source with no measured results of its own. | p1 0.67 / p2 0.05 | Below threshold (P1). Kept by user decision (first-pass sign-off). First read stopped at character 100000 of 136150 (SKIMMED); re-read to the end from the PDF. No figures recorded. |
| 3.12 | Anthropic, "Introducing Contextual Retrieval" | READ IN FULL | web | "Combining Contextual Embeddings and Contextual BM25 reduced the top-20-chunk retrieval failure rate by 49%" | Hybrid lexical plus semantic retrieval and a reranker cut missed-chunk rates in vendor tests on non-regulated corpora, with no abstention or compliance measure. | p1 0.98 / p2 0.99 | Vendor-published; results not independently replicated. |
| 3.13 | Qu et al., "Is Semantic Chunking Worth the Computational Cost?" | READ IN FULL | web | "The results show that the computational costs associated with semantic chunking are not justified by consistent performance gains." | Chunk strategy matters less than commonly assumed on natural documents; the paper does not test whether chunking splits required legal language, so that question is not answered here. | p1 0.95 / p2 0.99 | |
| 3.14 | Es et al., "RAGAS" | READ IN FULL | web | "Faithfulness refers to the idea that the answer should be grounded in the given context." | Faithfulness, answer relevance and context relevance are the standard automatic RAG metrics, and in this small test faithfulness tracked human judgment best (0.95) while context relevance tracked worst (0.70). | p1 0.94 / p2 0.99 | Claim 1 first run 0.61, reworded, re-run 0.97. |
| 3.15 | Saad-Falcon et al., "ARES" | READ IN FULL | web | "approximately 150 annotated datapoints or more." | A small human-labeled set (about 150 items) plus statistical correction gives a cheaper eval path than labeling everything, which fits a golden-set approach. | p1 0.92 / p2 0.99 | Introduction (59.3) and Section 5.1 (59.9) disagree on the gain over RAGAS; both recorded. Claim 1 first run 0.56, second 0.80, then split. |
| 3.16 | Jacovi et al., "The FACTS Grounding Leaderboard" | READ IN FULL | web | "use three different judge models in order to reduce the bias of a particular judge model" | A grounding benchmark exists for context-only answers, with a multi-judge design that limits self-preference, but its documents are general web text and not legal or policy language. | p1 0.91 / p2 0.99 | Authors' own models top the leaderboard. |
| 3.17 | NIST AI 600-1, Generative AI Profile | SKIMMED | web | "Review and verify sources and citations in GAI system outputs during pre-deployment risk measurement and ongoing monitoring activities." | NIST gives a documented basis for a launch gate that checks citations against sources and tests in conditions like deployment, but sets no numeric thresholds. | p1 0.79 / p2 0.17 | Below threshold (P1). Kept by user decision (first-pass sign-off). Only the confabulation, information integrity and pre-deployment testing sections were read, by plan. No figures recorded. |
| 3.18 | OWASP LLM08:2025, Vector and Embedding Weaknesses | READ IN FULL | web | "Implement fine-grained access controls and permission-aware vector and embedding stores." | OWASP names cross-group retrieval leakage as a documented risk and prescribes permission-aware stores and retrieval logging, without saying whether to filter before or after retrieval. | p1 0.80 / p2 0.18 | Below threshold (P1). Kept by user decision (first-pass sign-off). No figures recorded. |
| 3.19 | Microsoft Learn, Azure AI Search security trimming | READ IN FULL | web | "In this pattern, document-level authorization is enforced by applying the security filter to every query." | In this pattern the index carries a group-ID field per document and every query carries a filter built from the caller's groups, so the application must maintain the identity strings correctly and the search service does not authenticate them. | p1 0.97 / p2 0.86 | P2 passes but no numeric figure was recorded (qualitative numbers). The page does not label the filter pre- or post-filtering; ordering is inference and not recorded. |

---

### Learning Goal 4: What Medicare requires

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 4.1 | 42 CFR 422.2260, Definitions | READ IN FULL | web (eCFR) | "Communications means activities and use of materials created or administered by the MA organization or any downstream entity to provide information to current and prospective enrollees. Marketing is a subset of communications." | Communications is the umbrella; marketing needs both plan-selection or retention intent and benefits/cost/Star-type content, judged on objective context. | p1 0.88 / p2 0.15 | No figures recorded. Part D definitions (423.2260) not read. |
| 4.2 | 42 CFR 422.2267, Required materials and content | READ IN FULL | web (eCFR) | "Standardized materials and content are required materials and content that must be used in the form and manner provided by CMS." | Standardized content is alteration-limited and a few call-specific verbal items are tied to enrollment and sales calls, while nothing here addresses customer service or pharmacy education call scripts. | p1 0.97 / p2 0.97 | |
| 4.3 | 42 CFR 423.2267, Part D required materials and content | READ IN FULL | web (eCFR) | "For telephonic enrollments the contents of the PECL must be reviewed with the prospective enrollee prior to the completion of the enrollment." | Part D mirrors Part 422 and adds a standardized preferred-pharmacy limited-access statement that is the nearest analog to a pricing disclaimer verbatim. | p1 0.95 / p2 0.27 | No figures recorded (p2 below 0.85). The empty (b)(2) stem is in the eCFR text; Part D accompanying-language rule cited as (b)(3). |
| 4.4 | 42 CFR 422.2274, Agent, broker, and TPMO requirements (call recording) | READ IN FULL | web (eCFR) | "All marketing and sales calls, including the audio portion of calls conducted via web-based technology, must be recorded and retained in their entirety for a minimum period of 6 years." | Federal regulation requires TPMO marketing and sales calls be recorded and kept 6 years (3 as audio); no equivalent rule appears for customer service calls. | p1 0.96 / p2 0.99 | |
| 4.5 | 42 CFR 422.504, Contract provisions (paragraphs (d) and (e) only) | READ IN FULL (bounded paragraphs) | web (eCFR) | "The MA organization agrees to maintain for 10 years books, records, documents, and other evidence of accounting procedures and practices" | Plans must keep contract records 10 years and give CMS audit access, but the text does not name call recordings or script versions. | p1 0.65 / p2 0.99 | Below threshold (P1). Kept by user decision (LG4 sign-off 1). Not a protected category. |
| 4.6 | CMS Medicare Communications and Marketing Guidelines page and the 3-16-2022 PDF | READ IN FULL | web | "Marketing is a subset of communications and must, unless otherwise noted, adhere to all communication requirements." | The MCMG says a customer service call becomes marketing at the point the caller asks about other plans, and treats sales and enrollment scripts as CMS-submitted, versioned materials, but it is dated 2022 and its rule numbering is out of date. | p1 0.95 / p2 0.98 | Landing page was an orientation read (no Jev); PDF sent to Jev. Quote as 2022 guidance; currency not established. |
| 4.7 | CY2027 MA and Part D final rule, Federal Register 2026-06600 (marketing and communications sections) | READ IN FULL (bounded sections D to H of the preamble) | web (govinfo PDF of the same Federal Register issue; federalregister.gov returned a bot-check page) | "In summary, all marketing and sales calls, including the audio portion of calls conducted via web-based technology, must be recorded and retained in their entirety for a minimum period of 6 years." | The CY2027 rule sets 6-year retention with 3 years audio for TPMO marketing and sales calls, keeps enrollment records at 10 years, ties the "discussion of benefits" trigger to the marketing definition, and says nothing about AI in communications. | p1 0.97 / p2 0.99 | Rest of the 219-page rule searched by keyword only. Page cites approximate; cite section letters. Truncation: Part 423 amendment list condensed to section numbers in the Opus claim check. |
| 4.8 | CMS Part C and Part D Enforcement Actions page (index) plus the Humana CMP letter (01-17-2025) | READ IN FULL (index as a 71-row table from raw HTML; Humana letter in full) | web | "CMS has made a determination to impose a civil money penalty (CMP) in the amount of $99,064" | The enforcement index lists recent CMPs and sanctions without stating their subject, and the one Humana letter opened is a claims-processing penalty, not a communications case. | Index: not run (orientation read). Humana letter: p1 0.77 / p2 0.99 | Humana letter below threshold (P1). Kept by user decision (LG4 sign-off 1). First pass read the index only through WebFetch's summarizing model; the follow-up read the raw HTML. |
| 4.8.1 | CMS CMP letter, Centene Corporation (2025-01-17, $2,000,000) | READ IN FULL | web | "Centene failed to comply with Medicare requirements related Part C maximum out-of-pocket (MOOP) limit requirements" | Charged Part C enrollees above the annual maximum out-of-pocket limit because a claims system processed simultaneous claims independently. | Not run (orientation read) | Follow-up letter approved by user decision (LG4 sign-off 3). Not a communications case. |
| 4.8.2 | CMS CMP letter, CVS Health Corporation (2026-05-01, $753,805) | READ IN FULL | web | "CVS failed to comply with Medicare requirements related to Part C cost sharing requirements in violation of 42 C.F.R. Part 422, Subpart F" | Part C cost-sharing overcharges from five claims-system configuration errors found on financial audit. | Not run (orientation read) | Follow-up letter. Not a communications case. |
| 4.8.3 | CMS CMP letter, Centene Corporation (2026-05-01, $380,785) | READ IN FULL | web | NO QUOTE IN NOTES | Part C cost-sharing overcharges and MOOP overages from claims-system configuration and accumulator errors. | Not run (orientation read) | Follow-up letter. Not a communications case. |
| 4.8.4 | CMS CMP letter, Molina Healthcare, Inc. (2025-04-01, $285,476) | READ IN FULL | web | "Molina inappropriately rejected formulary medications due to errors with enrollees' eligibility files" | Part D claims rejected as "coverage terminated" because of an inaccurate eligibility file sent to the PBM. | Not run (orientation read) | Follow-up letter. Not a communications case. |
| 4.8.5 | CMS CMP letter, Elevance Health, Inc. (2025-01-17, $149,060) | READ IN FULL | web | NO QUOTE IN NOTES | Part C cost-sharing overcharges and MOOP overages from claims-system configuration errors. | Not run (orientation read) | Follow-up letter. Not a communications case. |
| 4.8.6 | CMS CMP letter, The Carle Foundation (2025-01-17, $101,500) | READ IN FULL | web | NO QUOTE IN NOTES | MOOP overages from manual claims processing that skipped the limit check. | Not run (orientation read) | Follow-up letter. Not a communications case. |
| 4.8.7 | CMS sanction letter, Elevance Health, Inc. (2026-02-27, suspension of enrollment and communications) | SKIMMED (10-page letter read for summary, legal basis and every use of communication or marketing, not line by line) | web | "substantial and persistent noncompliance with Medicare Advantage risk adjustment data submission requirements" | Risk adjustment data corrections sent on encrypted USB drives instead of CMS systems since 2018; the sanction suspends communication activities but the violation is not about communications. | Not run (orientation read) | Follow-up letter. Status assigned from the notes' description of the read. |
| 4.8.8 | CMS sanction letter, Aspirus Health Plan, Inc. (2026-02-24, suspension of enrollment) | SKIMMED (read from the Re: line through basis and corrective sections; per-letter status not stated in notes) | web | "Aspirus is failing substantially to carry out its contract with CMS ... because it is not able to accept new enrollments." | Wisconsin cease-and-desist order tied to a third-party administrator (which also provides customer service) left the plan unable to accept enrollments. | Not run (orientation read) | Follow-up letter. Status assigned from the notes' description of the read. |
| 4.8.9 | CMS notice of enrollment suspension, Wellcare of Missouri Health Insurance Company, Inc. (2024-09-06) | READ IN FULL (basis, violation and directive sections; pages 3 to 4 procedural, not read in detail) | web | "Wellcare of Missouri must ensure that its marketing and communications materials and activities are not misleading to beneficiaries" | CMS pairs a mandatory enrollment closure with an explicit instruction that marketing and communications must reflect it accurately, but states no finding that communications were wrong. | p1 0.97 / p2 0.99 | Follow-up letter. "CMS found inaccurate communications" claim scored 0.06 and was dropped. Counted "partial", not as a communications case. |
| 4.8.10 | CMS notice of enrollment suspension, MMM Healthcare, LLC (2026-09-03) | READ IN FULL (basis, violation and directive sections; page 4 procedural, not read in detail) | web | "MMM Healthcare must ensure that its marketing and communications materials and activities are not misleading to beneficiaries" | The 2026 MMM notice repeats the 2024 Wellcare directive almost word for word, so CMS treats accurate communication of an enrollment closure as a standing expectation, not a case-specific finding. | p1 0.96 / p2 0.99 | Follow-up letter. Same dropped claim at 0.06. Counted "partial". |
| 4.8.11 | CMS termination letter, UCare Minnesota (2025-09-22) | SKIMMED (procedural pages not read in detail; per-letter status not stated in notes) | web | "UCare failed to execute those contracts with CMS by the contract execution deadline" | Failed to sign 2026 contracts by the deadline; termination plus parallel enrollment and marketing suspension. | Not run (orientation read) | Follow-up letter. Status assigned from the notes' description of the read. |
| 4.8.12 | CMS termination and sanction letter, Clear Spring Health Insurance Company (2023-10-13) | SKIMMED (procedural pages not read in detail; per-letter status not stated in notes) | web | "failing to achieve a Part D summary Star Rating of at least three stars in three consecutive Star Rating periods" | Part D summary Star Rating below three stars for three consecutive years; parallel enrollment and marketing suspension. | Not run (orientation read) | Follow-up letter. Status assigned from the notes' description of the read. |
| 4.9 | CMS CMP letter, Aetna Inc. (2015), inaccurate pharmacy network information | READ IN FULL | web | "Aetna's website, pharmacy search tool, and customer service representatives are vital sources of information that beneficiaries rely on to make informed decisions on health coverage." | CMS fined Aetna $1,000,000 in 2015 for wrong in-network pharmacy information delivered on its website and by call center customer service representatives. | p1 0.92 / p2 0.99 | Named case. Claim 1 first draft 0.84, re-run 0.95. Penalty rests on 423.128, not Subpart V. |
| 4.10 | CMS CMP letter, InnovaCare (2013), inaccurate ANOC/EOC | READ IN FULL | web | "InnovaCare incorrectly stated that beneficiaries do not have a coverage gap." | CMS fined InnovaCare $49,710 in 2013 because its combined ANOC and EOC wrongly said there was no coverage gap, affecting 4,971 members. | p1 0.96 / p2 0.99 | Named case. Claim 1 first draft 0.63, split, re-run 0.95 and 0.98. Document case, not a call case. |
| 4.11 | CMS CY 2025 Part C and Part D Program Audit and Enforcement Report | READ IN FULL | web | "Dismissal notices omitted required language regarding vacating dismissals and requesting reconsideration." | CMS's own 2025 audit report names inconsistent notice updates across systems and vendors as a finding, but its 14 listed penalties are for cost-sharing and payment errors, not member communications. | p1 0.96 / p2 0.99 | The "CMPs At-a-Glance" figures were paired from layout. Organization names differ from the index; each cited as its own source gives it. |
| 4.12 | CMS 2022 Part C and Part D Call Center Monitoring memo | READ IN FULL | web | "Contracts with only Special Needs Plans (SNPs) are excluded from the accuracy measure." | CMS secret-shops plan call centers for hold time, interpreter and TTY access, and CSR accuracy on plan information, but the memo prescribes no script language. | p1 0.96 / p2 0.99 | 2022 guidance; no later-year memo in the original set. Claim 1 first run 0.83 and a negative claim 0.62 were reworded and split; the "no script" statement is the reader's inference. |
| 4.13a | CMS FAQ on coverage criteria and use of algorithms and AI (Feb 6, 2024), AAMC-hosted copy | SKIMMED | web (third-party AAMC copy; no cms.gov copy found) | "Because publicly posted coverage criteria are static and unchanging, artificial intelligence cannot be used to shift the coverage criteria over time." | CMS's one AI-specific MA memo says plans may use AI to assist coverage decisions but remain responsible for compliance, and it says nothing about AI in member communications. | p1 0.91 / p2 0.14 | Questions 1, 2 and 14 read in full; others by keyword. No figures recorded. Over-range item approved at sign-off (LG4 13 sources). |
| 4.13b | HHS AI Strategy press release (Dec 4, 2025) | COULD NOT ACCESS: HTTP 403 (WebFetch); no fallback listed | none (not read) | none | Not read; HHS-level AI guidance as of late 2026 remains unverified from this source. | Not run (nothing read) | A further attempt with a changed user agent was refused by the permission classifier and not run. Q5 on HHS guidance stays unanswered from this source. |
| 4.14 | CMS HPMS memo, 2026 Part C and Part D Call Center Monitoring (dated Dec 1, 2025) | READ IN FULL | local PDF (third-party-hosted copy; no cms.gov copy found; authenticity not checked) | "Part C and D call centers are required to maintain an average hold time of two minutes or less and an average disconnect rate of five percent or less." | The December 2025 CMS memo tests CSR accuracy on prospective enrollee lines and hold time and disconnects on enrollee and pharmacy help desk lines, and prescribes no call language, recording rule or AI position. | p1 0.97 / p2 0.99 | Added by user-approved follow-up to settle the Rx disclaimer framing question. Two claim-check calls. One audit record (0.69) not recorded in notes. |
| 4.15 | 42 CFR 422.111, paragraph (h) only | READ IN FULL (paragraph (h)(1) to (h)(3)) | web (eCFR) | "Each MA organization must have mechanisms for providing specific information on a timely basis to current and prospective enrollees upon request." | Paragraph (h) sets call center hours and speed-of-service standards for an MA plan and prescribes no call wording, accuracy duty, recording rule or AI position. | p1 0.97 / p2 0.99 | Added source. Truncation: (h)(2)(ii) shortened and (h)(2)(iii) omitted; total evidence per call exceeded 2,000 characters. Silence answers are inference. |
| 4.16 | 42 CFR 423.128, paragraph (d) only | READ IN FULL (paragraphs (d)(1) to (d)(5)) | web (eCFR) | "For coverage beginning on and after January 1, 2022, provides the information described in paragraph (d)(4) of this section to enrollees who call the customer service call center." | Paragraph (d) adds pharmacy-facing call center hours and requires callers to receive the (d)(4) cost sharing, formulary alternative and formulary status information, which it calls "complete, accurate, timely", but prescribes no wording. | p1 0.97 / p2 0.99 | Added source. Truncation: four sub-paragraphs omitted; total evidence per call exceeded 2,000 characters. "One business day" audit record (0.59) not recorded for 4.16. |

LG4 framing decision (sign-off "framing and LG5 start"): the deck presents the Rx pricing disclaimer as wording the plan's Legal team requires, with 423.2267(e)(40) cited only as a similar case, states that CMS call center rules and guidance name no required wording on customer service or pharmacy calls, and adds that 423.128(d)(1)(vi) and (d)(4) require cost sharing and formulary information given to Part D callers to be accurate and timely.

---

### Learning Goal 5: Who has tried this, and what transfers

#### Palantir (5.1 to 5.14)

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 5.1 | Ontology overview | READ IN FULL | web | "The Palantir Ontology is an operational layer for the organization." | Palantir's own definition of the Ontology is a semantic and action layer over operational datasets, not a store for prose. | p1 0.86 / p2 0.04 | Vendor documentation. Truncation: first three paragraphs only sent to Jev. |
| 5.2 | Ontology core concepts | READ IN FULL | web | "Roles are the central permissioning model in the Ontology." | the unit of governance is a typed object with properties; the page defines no concept of a prose unit, a version of an object, or an expiry. | p1 0.88 / p2 0.03 | Vendor documentation. |
| 5.3 | Action types overview | READ IN FULL | web | "An action is a single transaction that changes the properties of one or more objects, based on a user-defined logic." | actions are the governed write path; "latest version with edits" is the only versioning concept stated on this page. | p1 0.39 / p2 0.04 | Below threshold (P1). Protected category (Palantir), not deprioritized. |
| 5.4 | Markings concepts | READ IN FULL | web | "Markings are a mandatory control, while roles are a discretionary control." | marking inheritance is the strongest documented propagation mechanism in the corpus, and it is defined for datasets and files, not for passages of prose. | p1 0.87 / p2 0.05 | The healthcare example on the page is hypothetical. |
| 5.5 | Object permissioning overview | READ IN FULL | web | "These resources do not refer to the actual property values or primary key values; the actual property values and primary key values are contained in the objects and links." | a short index page; it confirms the two-level split but not how object-level filters are evaluated. | p1 0.76 / p2 0.84 | Below threshold (P1 and P2). Protected category, not deprioritized. No figure recorded (only an illustrative number on the page). |
| 5.6 | Data Lineage overview | READ IN FULL | web | "Visualize your pipeline through coloring (e.g. color out-of-date tables)" | lineage here traces datasets and transforms, which would map to source-document-to-unit tracing only if documents were ingested as datasets. | p1 0.81 / p2 0.04 | Below threshold (P1). Protected category, not deprioritized. |
| 5.7a | AIP Logic overview | READ IN FULL | web | "Logic functions can also be automated so that Ontology edits can be automatically applied or staged for human review." | grounding is by Ontology object input, and the page states that its row and column read controls "do not extend to the model's output or any Ontology edits it composes", so output protection depends on a marking or CBAC. | p1 0.95 / p2 0.04 | Split item (5.7 covers two URLs). Permissions wording revised and re-checked in Opus review (4 claims at 0.99). The linked Access control propagation page was not read. |
| 5.7b | AIP security and privacy | READ IN FULL | web | "When Palantir AIP leverages third-party-hosted model services, no customer data contained in prompts or completions is retained by the applicable third party." | a privacy and contracts FAQ, useful for the BAA point and not for how answers are grounded. | p1 0.91 / p2 0.04 | Split item. Company-stated assurances. Reader labels it not_relevant to prose governance; stands after Opus review. |
| 5.8 | AIP Evals overview | READ IN FULL | web | "AIP Evals allows you to create test cases, define evaluation functions to measure performance, and compare the results against previous versions of your function." | Evals is a generic regression-test harness for LLM functions; the evaluation metrics are user-defined. | p1 0.83 / p2 0.05 | Below threshold (P1). Protected category, not deprioritized. |
| 5.9 | Palantir FY2025 Annual Report (Form ARS) | SKIMMED | web (sec.gov PDF) | "Third-party AI capabilities that can be integrated with our platforms could also produce false or "hallucinatory" inferences about customer data or enterprises, or other information or subject matter." | Palantir's own filing claims propagation, provenance, retention and review checkpoints, and names healthcare only as a partnership target, with no disclosed healthcare result. | p1 0.90 / p2 0.99 | Item 1 read in full; Item 1A risk factors sampled by search. The filing has no healthcare section. Capability statements are company-stated. Privacy incident on the first fetch (see access-failures.md). Not re-checked in Opus review (sec.gov returned HTTP 403). Claim 0.69 reworded to 0.97. |
| 5.10 | Cognizant and Palantir TriZetto partnership (Feb 5, 2026) | READ IN FULL | web | "establish a secure, governed foundation for future AI-enabled capabilities" | a partnership announcement, not a deployment; it discloses no scope or results. | p1 0.83 / p2 0.27 | Below threshold (P1). Protected category, not deprioritized. No figures recorded. Partner-published, company-stated. Exploratory wording only. |
| 5.11 | GNP Seguros expansion of Foundry and AIP (Business Wire, Jul 7, 2026) | READ IN FULL | user-pasted text | "GNP Seguros has used Palantir’s Foundry and Artificial Intelligence Platform (AIP) in targeted deployments to detect claims fraud, monitor risk, and improve underwriting." | a company-stated expansion announcement for an insurer, using Foundry and AIP on claims, underwriting and risk data, with governance asserted in general terms and no results or prose governance. | p1 0.95 / p2 0.42 | Automated access failed (empty reply, 403); user pasted the text (sign-off, LG5 review questions). No figures recorded. Company-stated; copy not compared to the live page. |
| 5.12a | NHS England, FDP evaluating benefits | READ IN FULL | user-pasted text | "OSR identified further steps to ensure the way benefits are communicated is reflective of the underlying data and methods which we are committed to." | NHS England's own page confirms an independent evaluation is commissioned and that the OSR asked for further steps on how benefits are communicated, and reports no benefit figure. | p1 0.46 / p2 0.36 | Split item. Bot challenge on the live page; user pasted the text (sign-off, LG5 review questions). Below threshold (P1); Palantir deployment category protected, kept. The Imperial evaluation plan and OSR statement were not supplied. Link to Palantir rests on 5.12b and the plan's framing. |
| 5.12b | The Register, "Some English hospitals doubt Palantir's utility" (16 May 2025) | READ IN FULL | web | "From the descriptions we have of these FDP products we believe we would lose functionality rather than gain it by adopting them." | independent reporting of trust-level doubt about FDP functionality sits against NHS England's unquantified claim that the platform is delivering. | p1 0.95 / p2 0.99 | Split item. Independent press. Denominators for trusts differ within the article; each figure recorded with its attribution. |
| 5.13 | AIP Document Intelligence overview | READ IN FULL | web | "AIP Document Intelligence is Foundry's entry point for all document extraction workflows." | Palantir documents an ingestion path for PDFs, but the governance described elsewhere attaches to datasets and objects, and this page says nothing about governing the meaning of extracted prose. | p1 0.93 / p2 0.07 | Replaced the forum thread at original sign-off. |
| 5.14 | HASH, "The problem with Palantir" (April 3rd, 2025) | READ IN FULL | web | "Permissions cannot be exported between different data backbones" | a competitor's lock-in argument; relevant to exit cost and permission portability, not to the quality of Palantir's governance. | p1 0.94 / p2 0.05 | Interested-party critique (HASH sells an open-source competitor). Claim reworded to the "A Closed-Source System" section, 0.96 after Opus review. |

#### Moved out of the Palantir section by user decision

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 5.36 | GAO-21-600, "COVID-19: HHS's Collection of Hospital Capacity Data" (Aug 2021) | READ IN FULL | web (NLM fallback PDF; gao.gov returned HTTP 403) | "Stakeholders told us that the lack of clear definitions left data elements open to interpretation and people tasked with entering the data could interpret the data elements differently." | an independent audit of a COVID data platform with useful lessons on definitions and change management, but it does not mention Palantir. | p1 0.35 / p2 0.97 | Moved out of the Palantir section by user decision (LG5 review question 3). Used only as a lesson on shared definitions and reporting standards. Not evidence about Palantir. The report never names Palantir; no approved source establishes Palantir's role in HHS Protect. |

#### Enterprise search, contact center knowledge, and health insurer precedents (5.15 to 5.35)

| ID | Source | Status | Provenance | Proof of reading | Takeaway | Jev Stage 1 | User decisions and notes |
|---|---|---|---|---|---|---|---|
| 5.15 | Glean security principles | READ IN FULL | web | "Glean mirrors the access controls of every connected source system." | Glean documents ACL mirroring and citation limited to openable documents, but governs who can read, not which version of content is authoritative. | p1 0.96 / p2 0.03 | Vendor documentation. Page is silent on pre-filter versus post-filter. |
| 5.16 | Glean healthcare page | READ IN FULL | web | "Give providers, payers, and life sciences teams an AI coworker that helps them reduce administrative friction, respond faster, and improve outcomes across care, coverage, and research." | marketing page with no named customer and no figures; use only as evidence that Glean pitches payers. | p1 0.75 / p2 0.04 | Below threshold (P1). Enterprise search, not protected. Kept by user decision (LG5 review question 4). |
| 5.17 | Microsoft 365 Copilot oversharing blueprint (landing page) | READ IN FULL (landing page only, by user decision) | web | "Microsoft Copilot can accelerate how people find information, summarize content, and get work done by grounding responses in the data users already have permission to access." | Microsoft's own guidance treats oversharing as the main deployment risk to fix before Copilot, but the page is a short landing page with no detail on mechanism. | p1 0.88 / p2 0.27 | Landing page only; linked PDF not read (LG5 review question 5). No figures recorded. Live page title differs from the label in sources.md. |
| 5.18 | Microsoft blog, mitigating oversharing to govern Copilot and agents | READ IN FULL | user-pasted text | "Most internal oversharing stems from configuration issues rather than malicious user intent." | Microsoft documents that Copilot inherits user permissions and lists the controls (RCD, label-based DLP, lifecycle and retention) that clean or hide content before retrieval, but they govern access and recency, not which version is approved. | p1 0.96 / p2 0.98 | Automated access failed (HTTP 403); user pasted the text (LG5 user-supplied text sign-off). Copy not checked against the live page. Gartner figure inside is second-hand. |
| 5.19 | Gemini Enterprise, connectors and data stores | READ IN FULL | web | "An incremental sync periodically captures entity data that has been added or updated since the last sync. It does not sync identity data or deletions of entity data." | Gemini Enterprise documents an ACL-and-identity-sync model with explicit sync lags, built for ingesting heterogeneous source systems, with no content approval or version concept. | p1 0.96 / p2 0.98 | Stage 1 and claim check were first sent as one merged call, then re-run as two separate calls in the Opus review; the merged result is superseded. The scoping claim about an access-control setting that cannot be changed is not on the page. |
| 5.20 | Gemini Enterprise, custom connector ACLs | READ IN FULL | web | "Identity mapping: This method is used when the data source uses usernames, legacy IDs, or other external identity systems" | ACLs ride on every ingested document and external identities must be flattened and mapped up front; nothing on the page governs content approval or versions. | p1 0.86 / p2 0.28 | No figures recorded. |
| 5.21a | Coveo, Basic secured search | READ IN FULL | web | "In other words, the search results to display are the items matching the query, minus the items that the querying user isn't allowed to access." | Coveo has the most explicit public description of ACL-in-index plus query-time identity matching and default deny, and extends it to generated answers, but the content it secures is whatever was indexed. | p1 0.96 / p2 0.03 | Split item. The match-then-remove reading is labeled inference. Neither page documents citation of generated answers (scoping correction). Notes carry one takeaway for 5.21. |
| 5.21b | Coveo, RGA data security | READ IN FULL | web | "RGA's two-stage content retrieval ensures that Coveo controls the data used to generate the answer." | Same as 5.21a (the notes carry one takeaway for entry 5.21) | p1 0.96 / p2 0.40 | Split item. No figures recorded. |
| 5.22 | Coveo Humana case study (casestudies.com listing) | READ IN FULL (listing only; linked case study not followed) | web | "boosted search click-through rates from roughly 50% to 95%" | Humana is a named Coveo customer for web and finder search, with a company-stated click-through gain; it is not evidence of governed agent-facing knowledge. | p1 0.96 / p2 0.99 | Undated listing (COVID reference suggests 2020 or 2021, inference). Company-stated. Two claim wordings (0.80, 0.83) were reworded and re-run. |
| 5.23 | eGain AI Knowledge Suite for Health Plans | READ IN FULL | web | "Every answer is versioned, approved, and auditable down to the source." | the closest vendor description of the case's design, but it is a marketing page with one testimonial and one unsupported figure. | p1 0.93 / p2 0.98 | Company-stated marketing. |
| 5.24 | eGain release, leading US health insurer selects eGain | COULD NOT ACCESS: HTTP 404 (curl and WebFetch); user confirmed it is a true 404 | none (not read) | none | none. | Not run | Stays COULD NOT ACCESS (sign-off, LG5 user-supplied text). Contents not inferred. |
| 5.25 | Verint, UnitedHealth Group case study (video page) | READ IN FULL (page text only; video not played) | web | "uses Verint Knowledge Management as an integral component of its digital-first engagement strategy for both its customers and employees." | a thin video-page summary naming UHG as a Verint KM customer; the useful detail is on 5.26. | p1 0.80 / p2 0.97 | Below threshold (P1). Protected category (contact center knowledge), not deprioritized. |
| 5.26 | Verint, UnitedHealth Group standardizes enterprise-wide | READ IN FULL | web | "Knowledge articles are stored once and accessed often, as opposed to having to utilize additional storage via replication" | the only named large-payer contact center knowledge deployment in the set, with scale figures and a Stars motivation, but every outcome is Verint-published and the governance mechanics are only described at headline level. | p1 0.97 / p2 0.99 | Company-stated. Figures claim at 0.82 was reworded to 0.97. Undated page. |
| 5.27 | Salesforce Knowledge Developer Guide, articles and data categories | READ IN FULL | web | "Administrators can use data categories to control access to articles." | Salesforce documents a clean article lifecycle, version model, and role- and category-based audience scoping, which are the mechanics a verbatim-unit store needs, but not the approval workflow itself. | p1 0.97 / p2 0.86 | The page has no approval content (scoping correction). Figures are configuration counts, not results. |
| 5.28 | Shelf Help, advanced scores in Content Intelligence | READ IN FULL | web | "Contradictions happen when two statements are extremely unlikely to answer the same question." | Shelf is the only source in the set that documents exact, partial, near-duplicate, and contradiction detection. The partial-duplicate check matches the case's three-wordings failure only if the wordings share identical sections; the page sets the near-duplicate rule at 99% or higher similarity, and whether three slightly different disclaimer wordings would reach 99% is not stated (inference). | p1 0.93 / p2 0.96 | Numbers on the page are rule thresholds, not results. The scoping claim of an unnamed Fortune 50 healthcare case is not on this page. |
| 5.29 | Shelf contact center knowledge solution page | READ IN FULL | web | "Shelf continuously monitors your repositories, detects outdated, duplicate, conflicting, and low-quality content, and surfaces issues before they lead to inaccurate answers or poor customer experiences." | Shelf pitches governed, continuously QA'd knowledge for AI with non-payer references only; the detailed mechanics are on 5.28. | p1 0.96 / p2 0.99 | Company-stated marketing. No payer named. |
| 5.30 | CX Today, Gartner Magic Quadrant for CS-KMS 2026 rundown | READ IN FULL (the article; the Gartner report was not requested) | web | "Eight vendors make the cut across four quadrants." | independent press confirms the market now has a Gartner quadrant with eGain, Salesforce, and Shelf as Leaders, which supports the segment selection but gives no deployment evidence. | p1 0.97 / p2 0.98 | Analyst-derived, second-hand. Leaders claim reworded after 0.70 and 0.37. The Verint, Guru, ServiceNow absence claim (0.83) is kept as inference. |
| 5.31a | Humana, Agent Assist built with Google Cloud (Feb 2026) | READ IN FULL | web | "Humana member advocates began using Agent Assist in October 2025, with full rollout planned for Humana member service centers in 2026." | the largest named Medicare Advantage payer precedent in the set discloses scale, stack, and a human-in-the-loop principle but no governance mechanism and no results. | p1 0.94 / p2 0.98 | Split item. Company-stated. No source ties "Gemini Enterprise for CX" to the connectors in 5.19 and 5.20. |
| 5.31b | Fierce Healthcare, "Humana taps Google Cloud for new Agent Assist AI tool" (Feb 3, 2026) | READ IN FULL | user-pasted text | "Humana said the tool is seamlessly integrated into the existing workflow and undergoes routine and regular reviews to ensure compliance and performance." | Fierce adds no independent corroboration, so Humana's governance claims (compliance support, routine reviews, human in the loop) remain company-stated, but it supplies the "routine and regular reviews" wording, the consistency claim, and the Google executive quote that the release notes lacked. | p1 0.91 / p2 0.98 | Split item. Cloudflare challenge on the live page; user pasted the text (sign-off, LG5 user-supplied text). One stray placeholder call was made during this work (see access-failures.md). |
| 5.32 | UnitedHealthcare, Avery AI companion (Mar 2026) | READ IN FULL | web | "Avery provides a full synopsis to advocates if deeper support is necessary" | a Medicare Advantage-inclusive generative assistant with adoption and deflection numbers and a governance sentence, but no disclosed content governance. | p1 0.96 / p2 0.99 | Company-stated. Silence claim scored 0.65 and stays inference. |
| 5.33 | Elevance Health, how AI helps improve the consumer experience | READ IN FULL | web | "A program that automates post-call wrap-up summaries." | Elevance describes agent-assist features at headline level; its claim-explanation tool works from claims data, which makes it a contrast case for policy and script content. | p1 0.93 / p2 0.16 | No figures recorded. Company-stated. |
| 5.34 | Independence Blue Cross GenAI tool (Managed Healthcare Executive, Jun 2025) | READ IN FULL | web | "It also automatically generates documentation, allowing representatives to validate answers against the company's customer relationship management system." | a small payer pilot (more than 40 reps) with rep-side validation against the CRM and no disclosed content governance or results. | p1 0.96 / p2 0.99 | Trade press reporting an IBX release; the release was not read, so facts are second-hand and company-stated. First claim 0.51 reworded to 0.98. |
| 5.35 | Oscar Health, "Building a Superagent" | READ IN FULL | web | "If the LLM feels confident about the answer, it is returned to the member; otherwise, it is escalated to a human care guide" | Oscar is the most transparent payer disclosure found, with an explicit groundedness gate and extractive citations, but it governs retrieval and evals, not the authoring and approval of the source documents. | p1 0.97 / p2 0.99 | Company-stated engineering blog. Post year (2025) inferred. "About 400" questions in the text versus 422 in the table, as in the source. |

---


### Totals

Counts are rows in the tables above (split items count once per row). "Dropped or skipped" is a subset of the status columns: 1.11 is counted under READ IN FULL, 1.12 under COULD NOT ACCESS.

| Learning goal | Rows | READ IN FULL | SKIMMED | COULD NOT ACCESS | Dropped or skipped by user decision | Other user decisions |
|---|---|---|---|---|---|---|
| LG1 | 14 | 12 | 1 (1.9) | 1 (1.12) | 2 (1.11 dropped, 1.12 skipped) | 1.13 listing page only |
| LG2 | 12 | 11 | 1 (2.12) | 0 | 0 | |
| LG3 | 19 | 18 | 1 (3.17) | 0 | 0 | |
| LG4 | 29 | 23 | 5 (4.13a, 4.8.7, 4.8.8, 4.8.11, 4.8.12) | 1 (4.13b) | 0 | |
| LG5 Palantir (5.1 to 5.14) | 16 | 15 | 1 (5.9) | 0 | 0 | |
| LG5 moved (5.36) | 1 | 1 | 0 | 0 | 0 | 5.36 moved out of Palantir |
| LG5 other (5.15 to 5.35) | 23 | 22 | 0 | 1 (5.24) | 0 | 5.17 landing page only |
| Overall | 114 | 102 | 9 | 3 | 2 | |

---

## 7. Assumptions check

| Assumption | Verdict | Reasoning |
|---|---|---|
| Knowledge bases decay mainly because of duplication and missing ownership, rather than authoring tool limitations. | Partially confirmed | Duplication and stale content are top-ranked causes [1.8], and adopters cite volume incentives and approval bottlenecks [1.5][1.7]; Progress also blamed tool customizations [1.5], and findability ranked first [1.8]. |
| Search logs and failed searches are a reliable signal of missing content. | Partially confirmed | KCS prescribes "no match found" queries as a signal and a named adopter used search strings [1.1][1.5], but KCS separates findability failures from content gaps [1.1] and no source measures the signal's reliability. |
| Structured, single-source content worked at scale in a regulated industry before generative AI. | Partially confirmed | FDA SPL is a regulator standard [2.12] and medical-device DITA programs report results [2.4][2.5]; outcomes are company-stated and approval granularity limited reuse [2.6]. |
| Retrieval over raw, unclassified documents produces inconsistent or non-compliant answers, and documented incidents exist. | Partially confirmed | Incidents are documented [3.1][3.2] and legal RAG tools hallucinated 17% to 33% [3.3], but neither incident states a retrieval cause. |
| Restricting answers to approved units and abstaining reduces harmful answers without making the system unusable. | Undetermined | No source tests approved-unit restriction; abstention gains are modest (2 to 10 points) and over-abstention is a documented risk [3.10][3.11][3.3]. |
| Medicare rules require specific verbatim language on certain member calls, and a plan must show which version was in effect at a given time. | Partially confirmed | Verbatim and spoken items exist for telephonic enrollment and sales calls [4.2][4.3]; none names customer service or pharmacy calls, and no source requires proof of the version in effect [4.14][4.15][4.16][4.5]. |
| Palantir has solved the governed single-source problem in adjacent spaces, and its approach transfers to unstructured policy and script content. | Partially confirmed for structured data; unsupported for transfer | Markings, roles and validated actions are documented [5.4][5.3]; no documented deployment governs prose and read controls do not extend to model output [5.7a][5.11][5.13]. |
| Glean and peers solve permission-aware retrieval well, and their limits come from ungoverned content. | Partially confirmed | Glean documents permission mirroring and scoped citations [5.15] and Microsoft says governance gaps "become amplified" [5.18]; "well" is not measured in any source. |
| Contact center knowledge vendors already sell most of this capability, so the gap is governance and operating model. | Partially confirmed | eGain markets the pattern and Verint describes it at UnitedHealth Group (CS) [5.23][5.26]; verbatim handling and approval mechanics are not documented, and the UHG account credits a center of excellence [5.26]. |
| AI-assisted extraction, deduplication and drift detection are accurate enough with human review but not without it. | Undetermined | No source reports accuracy for duplicate, contradiction or drift detection [5.28][5.13]; automated citation checks agree with humans only 78% to 85% of the time [3.8], which supports keeping humans in the loop (inference). |

---

## 8. Likely interview questions this research prepares me for

1. **Why not point Glean or Copilot at the existing documents?** Both inherit permissions from the source systems and govern who can read, so three conflicting copies would all stay retrievable [5.15][5.18]. Models adopt wrong retrieved text over 60% of the time [3.6]. The risk is the content itself, so the fix has to start with the content.

2. **Is the Rx pricing disclaimer actually required by CMS on these calls?** No rule I read names customer service or pharmacy education calls. The verbatim and spoken requirements I found cover telephonic enrollment and sales calls [4.2][4.3]. I treat the disclaimer as wording Legal requires. Separately, the Part D call center rule requires cost-sharing information given to callers to be accurate and timely [4.16], and CMS fined Aetna $1,000,000 when its call center gave wrong pharmacy information [4.9].

3. **Why extractive answers for verbatim instead of letting the model phrase it?** CMS standardized content allows no alteration beyond listed edits [4.2]. Generated citations are frequently unsupported: only 51.5% of sentences in generative search were fully supported [3.9]. Returning the approved text exactly, and citing the unit, makes compliance checkable.

4. **How do you set the abstention threshold?** Outside the model, on a golden set. Models hallucinate more often than they abstain [3.10], and their confidence may be miscalibrated [3.11]. I tune for correct abstention and measure over-abstention, and every abstention goes to the authoring backlog [1.1].

5. **What is your launch gate?** No regulated team I read published a numeric gate, except Oscar's company-stated 90% groundedness [5.35]. I propose:
   - 100% exact match on verbatim units;
   - citation precision and recall [3.8];
   - faithfulness [3.14];
   - correct abstention;
   - zero cross-scope leaks [3.18].

   The golden set would have roughly 150 or more labels [3.15], with monitoring after launch [3.17].

6. **Isn't this what eGain or Verint already sell?** eGain markets a versioned, approved, audited layer for health plans, and Verint describes UnitedHealth Group's 80,000-article central platform. Both are company-stated [5.23][5.26]. Neither source shows how verbatim is stored, how all copies are found, or how the version in effect is proven. Those are the questions for a vendor demo, and the operating model is the part a vendor cannot supply [5.26][1.1].

7. **Does Palantir solve this?** Partly. It documents markings that travel with data, a validated write path, and staged human review [5.4][5.3][5.7a]. Its documented controls are for structured data. Its read controls "do not extend to the model's output" [5.7a]. The insurer deployment I read covers claims and underwriting data [5.11].

8. **How will you find every copy of the disclaimer today and prove later which version was used?** Migration runs identical-section and near-duplicate detection, with every hit sent to human review [5.28]. After that, each unit carries a constant ID, a version number and an effective date, as in FDA SPL [2.12], and every channel renders it by reference [2.3]. CMS's own audits found notice updates applied inconsistently across systems and vendors [4.11], so a single referenced unit removes that failure mode.

---

## Appendix: final-wording Jev re-check

Claims whose wording changed materially in synthesis were re-checked with jev_noul at threshold 0.85, one source per call, against verbatim passages under 2,000 characters taken from the notes. One exception: the Carestream passage came from the saved raw page text, and was added to the 2.6 notes entry first. 13 calls covering 30 claims, all at or above 0.85 (range 0.90 to 0.98), no failures.

| Source | Claims checked | Probabilities |
|---|---|---|
| 2.6 Carestream | approval in context of deliverable; specs example; 12 roles; traceability | 0.98, 0.97, 0.98, 0.98 |
| 5.26 Verint at UHG | 2018 outage and Stars threat; 80,000 articles and roles; author approval, store once | 0.93, 0.96, 0.98 |
| 1.1 KCS | demand-driven review; no tolerance for variability; no-match queries to KDE; legacy migration; search cannot fix content | 0.98, 0.98, 0.94, 0.98, 0.98 |
| 4.9 Aetna CMP | penalty and cause; complaints; SEP and basis | 0.92, 0.97, 0.90 |
| 4.7 CY2027 rule | 6-year retention replacing 10; disclaimer and discussion of benefits | 0.96, 0.97 |
| 3.3 Magesh et al. | 17% to 33%; poor retrieval and inapplicable authority; Westlaw citation hypothesis | 0.95, 0.97, 0.98 |
| 5.31a Humana | scale, human in the loop, October 2025 start | 0.96 |
| 5.28 Shelf | duplicate, near-duplicate and contradiction checks | 0.91 |
| 1.9 NBER | productivity gains with knowledge base links; handle time and resolution | 0.91, 0.97 |
| 2.12 FDA SPL | set ID, version, effective date; core-document reference | 0.95, 0.96 |
| 4.16 423.128(d) | (d)(4) information to callers; pharmacy call center hours | 0.91, 0.97 |
| 5.18 Microsoft | permission inheritance amplifies governance gaps; configuration causes | 0.91 |
| 4.2 422.2267 | standardized content without alteration; spoken items on sales calls and telephonic enrollment | 0.98, 0.95 |

Claims taken from the notes with their wording unchanged keep the Jev results recorded in the notes.

---

## References

Status: READ IN FULL unless marked SKIMMED or COULD NOT ACCESS. "User-supplied copy" means the user provided the text after automated access was blocked.

- [1.1] KCS v6 Practices Guide, Section 2: The KCS Practices (Solve and Evolve loops, Content Health). https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030 (READ IN FULL; landing page as 1.1a, 11 widened pages as 1.1b)
- [1.2] KCS v6 Practices Guide, Appendix C: Metrics Matrix. https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/070 (READ IN FULL)
- [1.3] KCS Measurement Matters v6. https://library.serviceinnovation.org/KCS/KCS_v6/Measurement_Matters_v6 (READ IN FULL)
- [1.4] Article Quality Index is now Content Standard Checklist. https://www.serviceinnovation.org/aqi-is-content-standard-checklist/ (READ IN FULL)
- [1.5] KCS case study: Progress Software. https://library.serviceinnovation.org/Case_Studies/KCS_Case_Studies/850_Progress_Software_KCS_in_Application_Support_Services (READ IN FULL)
- [1.6] KCS case study: Omgeo (financial services), Evolve Loop. https://library.serviceinnovation.org/Case_Studies/KCS_Case_Studies/725_Omgeo_Improving_CX_with_KCS_Evolve_Loop (READ IN FULL)
- [1.7] KCS case study: ServiceNow, Faster Time to Relief. https://library.serviceinnovation.org/Case_Studies/KCS_Case_Studies/400_ServiceNow_KCS_Faster_Time_to_Relief (READ IN FULL)
- [1.8] Call Centre Helper, "Finding Information Quickly Is the Biggest Challenge" (2021 survey, n=224). https://www.callcentrehelper.com/finding-information-quickly-is-the-biggest-challenge-209541.htm (READ IN FULL)
- [1.9] Brynjolfsson, Li, Raymond, "Generative AI at Work," NBER w31161. https://www.nber.org/papers/w31161 (SKIMMED)
- [1.10] Salesforce, State of Service, 7th edition (PDF). https://www.salesforce.com/en-us/wp-content/uploads/sites/4/documents/PDF/state-of-service-7th-edition.pdf (READ IN FULL)
- [1.11] McKinsey, "Where is customer care in 2024?". https://www.mckinsey.com/capabilities/operations/our-insights/where-is-customer-care-in-2024 (READ IN FULL, dropped by user decision)
- [1.12] Gartner, Magic Quadrant for Customer Service KMS, abstract (2026). https://www.gartner.com/en/documents/8131229 (COULD NOT ACCESS: HTTP 403, Cloudflare challenge (paywalled))
- [1.13] Shelf case study: Fortune 50 healthcare, "60% content rot". https://www.casestudies.com/company/shelf-09/case-study/healthcare-eliminates-60-content-rot-and-reaches-95-fcr-with-shelf (READ IN FULL (listing page only, by user decision))
- [2.1] OASIS DITA 1.3, Part 0: Overview. https://docs.oasis-open.org/dita/dita/v1.3/dita-v1.3-part0-overview.html (READ IN FULL)
- [2.2] DITA 1.3 spec 2.4.2: Content reference (conref). https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part3-all-inclusive/archSpec/base/conref.html (READ IN FULL)
- [2.3] DITA 1.3 spec 2.4.2.1: Conref overview. https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part3-all-inclusive/archSpec/base/conref-overview.html (READ IN FULL)
- [2.4] RWS Tridion Docs, HORIBA Medical case study (PDF). https://rws.com/media/images/tridion-docs-horiba-medica-case-study-rws-en-a4_tcm228-205235.pdf (READ IN FULL)
- [2.5] Bluestream, GE Healthcare DITA case study. https://bluestream.com/case-studies/ge-healthcare/ (READ IN FULL)
- [2.6] DITAWriter, "DITA in the Healthcare Sector" (Carestream interview). https://ditawriter.com/dita-in-the-healthcare-sector (READ IN FULL)
- [2.7] Veeva PromoMats 2024 Innovation Guide (PDF). https://www.veeva.com/wp-content/uploads/2024/01/Promomats_Innovation-Guide_v7.pdf (READ IN FULL)
- [2.8] Veeva, "Modular Content Powers Omnichannel Engagement at Speed and Scale" (2023 PDF). https://pantheon.veeva.com/wp-content/uploads/2023/02/NA-Modular-Content-Powers-Omnichannel-Engagement-at-Speed-and-Scale.pdf (READ IN FULL)
- [2.9] Veeva, "Optimize MLR Workflows Using a Central Claims Library". https://www.veeva.com/resources/optimize-mlr-workflows-using-a-central-claims-library/ (READ IN FULL)
- [2.10] Veeva blog, Astellas and Merck KGaA MLR teams on modular content. https://www.veeva.com/blog/how-astellas-merck-kgaa-mlr-teams-view-the-modular-content-evolution (READ IN FULL)
- [2.11] Klick, "From Checkpoint to Input: A Different Model for MLR". https://idx.klick.com/articles/from-checkpoint-to-input-a-different-model-for-mlr (READ IN FULL)
- [2.12] FDA, Structured Product Labeling Resources. https://www.fda.gov/industry/fda-data-standards-advisory-board/structured-product-labeling-resources (SKIMMED)
- [3.1] Moffatt v. Air Canada, 2024 BCCRT 149. https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do (READ IN FULL)
- [3.2] The Markup, "NYC's AI Chatbot Tells Businesses to Break the Law" (2024). https://themarkup.org/news/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law (READ IN FULL)
- [3.3] Magesh et al., "Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools" (2024). https://arxiv.org/abs/2405.20362 (READ IN FULL)
- [3.4] Barnett et al., "Seven Failure Points When Engineering a RAG System" (2024). https://arxiv.org/abs/2401.05856 (READ IN FULL)
- [3.5] Chen et al., "Benchmarking LLMs in Retrieval-Augmented Generation" (RGB, 2023). https://arxiv.org/abs/2309.01431 (READ IN FULL)
- [3.6] Wu et al., "ClashEval" (2024). https://arxiv.org/abs/2404.10198 (READ IN FULL)
- [3.7] Liu et al., "Lost in the Middle" (2023). https://arxiv.org/abs/2307.03172 (READ IN FULL)
- [3.8] Gao et al., "Enabling LLMs to Generate Text with Citations" (ALCE, 2023). https://arxiv.org/abs/2305.14627 (READ IN FULL)
- [3.9] Liu, Zhang, Liang, "Evaluating Verifiability in Generative Search Engines" (2023). https://arxiv.org/abs/2304.09848 (READ IN FULL)
- [3.10] Joren et al., "Sufficient Context" (2024). https://arxiv.org/abs/2411.06037 (READ IN FULL)
- [3.11] Wen et al., "Know Your Limits: A Survey of Abstention in LLMs" (2024). https://arxiv.org/abs/2407.18418 (READ IN FULL)
- [3.12] Anthropic, "Introducing Contextual Retrieval" (2024). https://www.anthropic.com/news/contextual-retrieval (READ IN FULL)
- [3.13] Qu et al., "Is Semantic Chunking Worth the Computational Cost?" (2024). https://arxiv.org/abs/2410.13070 (READ IN FULL)
- [3.14] Es et al., "RAGAS" (2023). https://arxiv.org/abs/2309.15217 (READ IN FULL)
- [3.15] Saad-Falcon et al., "ARES" (2023). https://arxiv.org/abs/2311.09476 (READ IN FULL)
- [3.16] Jacovi et al., "The FACTS Grounding Leaderboard" (2025). https://arxiv.org/abs/2501.03200 (READ IN FULL)
- [3.17] NIST AI 600-1, Generative AI Profile (PDF). https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf (SKIMMED)
- [3.18] OWASP LLM08:2025, Vector and Embedding Weaknesses. https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/ (READ IN FULL)
- [3.19] Microsoft Learn, Azure AI Search security trimming. https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search (READ IN FULL)
- [4.1] 42 CFR 422.2260, Definitions (communications versus marketing). https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-V/section-422.2260 (READ IN FULL)
- [4.2] 42 CFR 422.2267, Required materials and content. https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-V/section-422.2267 (READ IN FULL)
- [4.3] 42 CFR 423.2267, Part D required materials and content. https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-V/section-423.2267 (READ IN FULL)
- [4.4] 42 CFR 422.2274, Agent, broker, and TPMO requirements (call recording). https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-V/section-422.2274 (READ IN FULL)
- [4.5] 42 CFR 422.504, Contract provisions (record retention, paragraph (d)). https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-K/section-422.504 (READ IN FULL (bounded paragraphs))
- [4.6] CMS, Medicare Communications and Marketing Guidelines page and the 3-16-2022 MCMG PDF. https://www.cms.gov/files/document/medicare-communications-and-marketing-guidelines-3-16-2022.pdf (READ IN FULL)
- [4.7] CY2027 MA and Part D final rule, Federal Register 2026-06600 (April 6, 2026). https://www.federalregister.gov/documents/2026/04/06/2026-06600 (READ IN FULL (bounded sections D to H of the preamble))
- [4.8] CMS Part C and Part D Enforcement Actions page. https://cms.gov/Medicare/Compliance-and-Audits/Part-C-and-Part-D-Compliance-and-Audits/PartCandPartDEnforcementActions-.html (READ IN FULL (index as a 71-row table from raw HTML; Humana letter in full))
- [4.8.1] Centene Corporation (CMP $2,000,000), 2025-01-17. https://www.cms.gov/files/document/centenecmp01172025.pdf (READ IN FULL)
- [4.8.2] CVS Health Corporation (CMP $753,805), 2026-05-01. https://www.cms.gov/files/document/cvscmp05012026.pdf (READ IN FULL)
- [4.8.3] Centene Corporation (CMP $380,785), 2026-05-01. https://www.cms.gov/files/document/centenecmp05012026.pdf (READ IN FULL)
- [4.8.4] Molina Healthcare, Inc. (CMP $285,476), 2025-04-01. https://www.cms.gov/files/document/molinacmp04012025.pdf (READ IN FULL)
- [4.8.5] Elevance Health, Inc. (CMP $149,060), 2025-01-17. https://www.cms.gov/files/document/elevancehealthcmp01172025.pdf (READ IN FULL)
- [4.8.6] The Carle Foundation (CMP $101,500), 2025-01-17. https://www.cms.gov/files/document/carlefoundationcmp01172025.pdf (READ IN FULL)
- [4.8.7] Elevance Health, Inc. (suspension of enrollment and communications), 2026-02-27. https://www.cms.gov/files/document/elevancehealthsanction02272026.pdf (SKIMMED (10-page letter read for summary, legal basis and every use of communication or marketing, not line by line))
- [4.8.8] Aspirus Health Plan, Inc. (suspension of enrollment), 2026-02-24. https://www.cms.gov/files/document/aspirussanction02242026.pdf (SKIMMED (read from the Re: line through basis and corrective sections; per-letter status not stated in notes))
- [4.8.9] Wellcare of Missouri Health Insurance Company, Inc. (enrollment suspension), 2024-09-06. https://www.cms.gov/files/document/wellcaremosanction09062024.pdf (READ IN FULL (basis, violation and directive sections; pages 3 to 4 procedural, not read in detail))
- [4.8.10] MMM Healthcare, LLC (enrollment suspension), 2026-09-03. https://www.cms.gov/files/document/mmmhealthcaresanctionnotice09032026.pdf (READ IN FULL (basis, violation and directive sections; page 4 procedural, not read in detail))
- [4.8.11] UCare Minnesota (termination), 2025-09-22. https://www.cms.gov/files/document/ucaretermination09222025.pdf (SKIMMED (procedural pages not read in detail; per-letter status not stated in notes))
- [4.8.12] Clear Spring Health Insurance Company (termination and sanctions), 2023-10-13. https://www.cms.gov/files/document/clear-spring-termination-sanction-10132023.pdf (SKIMMED (procedural pages not read in detail; per-letter status not stated in notes))
- [4.9] CMS CMP letter, Aetna (2015), inaccurate pharmacy network information. https://www.cms.gov/Medicare/Compliance-and-Audits/Part-C-and-Part-D-Compliance-and-Audits/Downloads/AetnaCMP4162015.pdf (READ IN FULL)
- [4.10] CMS CMP letter, InnovaCare (2013), inaccurate ANOC. https://www.cms.gov/Medicare/Compliance-and-Audits/Part-C-and-Part-D-Compliance-and-Audits/Downloads/InnovaCare-Inc-CMP-10_-24_13.pdf (READ IN FULL)
- [4.11] CMS 2025 Part C and Part D Program Audit and Enforcement Report. https://www.cms.gov/files/document/2025-part-c-part-d-program-audit-enforcement-report.pdf (READ IN FULL)
- [4.12] CMS 2022 Part C and Part D Call Center Monitoring memo. https://cms.gov/files/document/2022partcandpartdcallcentermonitoring.pdf (READ IN FULL)
- [4.13a] CMS FAQ on coverage criteria and use of algorithms and AI, Feb 6, 2024 (AAMC-hosted copy). https://www.aamc.org/media/74896/download?attachment (SKIMMED)
- [4.13b] HHS, "HHS unveils AI strategy to transform agency operations" (Dec 4, 2025). https://www.hhs.gov/press-room/hhs-unveils-ai-strategy-to-transform-agency-operations.html (COULD NOT ACCESS: HTTP 403 (WebFetch); no fallback listed)
- [4.14] CMS HPMS memo, "2026 Part C and Part D Call Center Monitoring" (9 pages, PDF created 2025-12-01). https://24393978.fs1.hubspotusercontent-na1.net/hubfs/24393978/2026%20Part%20C%20and%20Part%20D%20Call%20Center%20Monitoring.pdf (READ IN FULL)
- [4.15] 42 CFR 422.111, Disclosure requirements, paragraph (h) only. https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-C/section-422.111 (READ IN FULL (paragraph (h)(1) to (h)(3)))
- [4.16] 42 CFR 423.128, Dissemination of Part D plan information, paragraph (d) only. https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-423/subpart-C/section-423.128 (READ IN FULL (paragraphs (d)(1) to (d)(5)))
- [5.1] Ontology overview. https://www.palantir.com/docs/foundry/ontology/overview/ (READ IN FULL)
- [5.2] Ontology core concepts. https://www.palantir.com/docs/foundry/ontology/core-concepts/ (READ IN FULL)
- [5.3] Action types overview. https://www.palantir.com/docs/foundry/action-types/overview/ (READ IN FULL)
- [5.4] Markings concepts. https://www.palantir.com/docs/foundry/security/markings/ (READ IN FULL)
- [5.5] Object permissioning overview. https://www.palantir.com/docs/foundry/object-permissioning/overview/ (READ IN FULL)
- [5.6] Data Lineage overview. https://www.palantir.com/docs/foundry/data-lineage/overview/ (READ IN FULL)
- [5.7a] Palantir, AIP Logic overview. https://www.palantir.com/docs/foundry/logic/overview/ (READ IN FULL)
- [5.7b] Palantir, AIP security and privacy. https://www.palantir.com/docs/foundry/aip/aip-security/ (READ IN FULL)
- [5.8] AIP Evals overview. https://www.palantir.com/docs/foundry/aip-evals/overview/ (READ IN FULL)
- [5.9] Palantir FY2025 Annual Report (Form ARS). https://www.sec.gov/Archives/edgar/data/0001321655/000132165526000021/fy2025palantirars.pdf (SKIMMED)
- [5.10] Cognizant and Palantir TriZetto partnership (Feb 5, 2026). https://news.cognizant.com/2026-02-05-Cognizant-partners-with-Palantir-to-Accelerate-AI-Driven-Modernization-in-Healthcare-and-Enterprise-Operations (READ IN FULL)
- [5.11] GNP Seguros expansion of Foundry and AIP (insurer, health line). https://secure.businesswire.com/news/home/20260707514163/en/Palantir-Expands-Its-Presence-in-Mexico-and-Strengthens-Its-AI-Offering-in-the-Insurance-Sector-with-GNP-Seguros (READ IN FULL)
- [5.12a] NHS England, NHS Federated Data Platform: evaluating benefits. https://www.england.nhs.uk/digitaltechnology/nhs-federated-data-platform/impact/fdp-uptake-and-benefits/evaluating-benefits/ (READ IN FULL)
- [5.12b] The Register, "Some English hospitals doubt Palantir's utility" (16 May 2025). https://www.theregister.com/2025/05/16/nhs_hospitals_palantir/ (READ IN FULL)
- [5.13] AIP Document Intelligence overview (document extraction into Foundry: extraction strategies, evaluation, deplo. https://www.palantir.com/docs/foundry/document-intelligence/overview/ (READ IN FULL)
- [5.14] HASH, "The problem with Palantir". https://hash.ai/blog/the-problem-with-palantir (READ IN FULL)
- [5.15] Glean security principles. https://docs.glean.com/security/security-principles (READ IN FULL)
- [5.16] Glean healthcare page. https://glean.com/industries/healthcare (READ IN FULL)
- [5.17] Microsoft 365 Copilot oversharing blueprint. https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-blueprint-oversharing (READ IN FULL (landing page only, by user decision))
- [5.18] Microsoft blog, mitigating oversharing to govern Copilot and agents. https://techcommunity.microsoft.com/blog/microsoft365copilotblog/mitigate-oversharing-to-govern-microsoft-365-copilot-and-agents/4448744 (READ IN FULL)
- [5.19] Gemini Enterprise, connectors and data stores. https://docs.cloud.google.com/gemini/enterprise/docs/introduction-to-connectors-and-data-stores (READ IN FULL)
- [5.20] Gemini Enterprise, custom connector ACLs. https://docs.cloud.google.com/gemini/enterprise/docs/custom-connector (READ IN FULL)
- [5.21a] Coveo, Basic secured search. https://docs.coveo.com/en/1749/ (READ IN FULL)
- [5.21b] Coveo, Relevance Generative Answering data security. https://docs.coveo.com/en/nbpd4153/ (READ IN FULL)
- [5.22] Coveo Humana case study. https://www.casestudies.com/company/coveo/case-study/humana-ai-driven-relevance-for-customer-centric-healthcare (READ IN FULL (listing only; linked case study not followed))
- [5.23] eGain AI Knowledge Suite for Health Plans. https://www.egain.com/?p=37810 (READ IN FULL)
- [5.24] eGain release, leading US health insurer selects eGain. https://egain.com/?p=10214 (COULD NOT ACCESS: HTTP 404 (curl and WebFetch); user confirmed it is a true 404)
- [5.25] Verint, UnitedHealth Group case study. https://www.verint.com/case-studies/unitedhealth-group-capitalizes-on-millions-of-data-points-with-verint-knowledge-management/ (READ IN FULL (page text only; video not played))
- [5.26] Verint, UnitedHealth Group standardizes enterprise-wide. https://verint.com/case-studies/unitedhealth-group-standardizes-on-verint-knowledge-management-enterprise-wide (READ IN FULL)
- [5.27] Salesforce Knowledge Developer Guide, articles and data categories. https://developer.salesforce.com/docs/atlas.en-us.knowledge_dev.meta/knowledge_dev/knowledge_development_object_managing_articles.htm (READ IN FULL)
- [5.28] Shelf Help, advanced scores in Content Intelligence. https://help.shelf.io/advanced-scores-in-content-intelligence-5983adf3 (READ IN FULL)
- [5.29] Shelf contact center knowledge solution page. https://shelf.io/contact-center-knowledge-solution/ (READ IN FULL)
- [5.30] CX Today, Gartner Magic Quadrant for CS-KMS 2026 rundown. https://cxtoday.com/gartner-magic-quadrant-customer-service-knowledge-management-2026 (READ IN FULL (the article; the Gartner report was not requested))
- [5.31a] Humana, "Humana Redefines the Member Experience with Agent Assist Built with Google Cloud" (Feb 3, 2026). https://news.humana.com/news/articles/humana-redefines-the-member-experience-with-agent-assist-built-with-google-cloud (READ IN FULL)
- [5.31b] Fierce Healthcare, "Humana taps Google Cloud for new Agent Assist AI tool" (Feb 3, 2026). https://www.fiercehealthcare.com/payers/humana-taps-google-cloud-new-agent-assist-ai-tool (READ IN FULL)
- [5.32] UnitedHealthcare, Avery AI companion (Mar 2026). https://www.unitedhealthgroup.com/newsroom/2026/2026-03-26-uhc-introduces-ai-companion-empowering-people-with-simpler-navigation-personal-experience.html (READ IN FULL)
- [5.33] Elevance Health, how AI helps improve the consumer experience. https://www.elevancehealth.com/our-approach-to-health/digitally-enabled-healthcare/how-ai-helps-improve-the-consumer-experience (READ IN FULL)
- [5.34] Independence Blue Cross GenAI tool for customer service reps (Managed Healthcare Executive, Jun 2025). https://www.managedhealthcareexecutive.com/view/ibx-joins-growing-ai-wave-with-genai-tool-to-boost-customer-service-and-member-trust (READ IN FULL)
- [5.35] Oscar Health, "Building a Superagent". https://oscar-ai.squarespace.com/blog/building-a-superagent-how-were-using-ai-to-explain-healthcare-faster (READ IN FULL)
- [5.36] GAO-21-600, "COVID-19: HHS's Collection of Hospital Capacity Data" (Aug 2021). Independent audit of HHS Protec. https://www.gao.gov/products/gao-21-600 (READ IN FULL)
