# Stage 8 — GenAI: semantic retrieval over unstructured deal documents

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:15:11 UTC by `evidence/capture_evidence.py`._

**Deal Memory corpus (UC table; files also in Volume deal_memory)**

```sql
SELECT doc_id, advertiser_name, doc_type, source, effective_date, size(embedding) embedding_dim FROM cs_genie_research_catalog.ad_sales.deal_docs ORDER BY doc_id
```

| doc_id | advertiser_name | doc_type | source | effective_date | embedding_dim |
|---|---|---|---|---|---|
| DM001 | Meridian Retail (062) | contract | Renewal Insertion Order 2026 | 2026-03-01 | 1024 |
| DM002 | Meridian Retail (062) | recap | Q3 Campaign Wrap Report | 2026-08-20 | 1024 |
| DM003 | Meridian Retail (062) | qbr | QBR Notes — Aug 2026 | 2026-08-28 | 1024 |
| DM004 | Meridian Restaurants | recap | Primetime QSR Wrap | 2026-08-15 | 1024 |
| DM005 | Ironwood Health (040) | contract | Pharma Guaranteed-GRP Agreement | 2026-02-10 | 1024 |
| DM006 | Ironwood Health (040) | recap | Reach Wrap Report | 2026-08-18 | 1024 |
| DM007 | Ironwood Health (040) | qbr | Renewal QBR | 2026-08-25 | 1024 |
| DM008 | Halcyon Retail (061) | recap | Late-Night Wrap | 2026-08-12 | 1024 |
| DM009 | Halcyon Retail (061) | qbr | Budget QBR | 2026-08-22 | 1024 |
| DM010 | Atlas Retail (070) | recap | Scatter Wrap Report | 2026-08-10 | 1024 |
| DM011 | Atlas Retail (070) | contract | Renewal Terms w/ Viewability SLA | 2026-03-15 | 1024 |
| DM012 | Polaris Brands (045) | contract | Upfront Commitment | 2026-01-20 | 1024 |
| DM013 | Polaris Brands (045) | recap | CPG Wrap Report | 2026-08-19 | 1024 |
| DM014 | Emberly Retail (126) | recap | Holiday Wrap | 2026-08-05 | 1024 |
| DM015 | Pioneer Communications (134) | qbr | Telco Renewal QBR | 2026-08-26 | 1024 |

**Files in the UC Volume**

```sql
LIST '/Volumes/cs_genie_research_catalog/ad_sales/deal_memory/'
```

| path | name | size | modification_time |
|---|---|---|---|
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM001.txt | DM001.txt | 553 | 1792006130000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM002.txt | DM002.txt | 457 | 1792006130000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM003.txt | DM003.txt | 468 | 1792006131000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM004.txt | DM004.txt | 330 | 1792006131000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM005.txt | DM005.txt | 367 | 1792006132000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM006.txt | DM006.txt | 349 | 1792006132000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM007.txt | DM007.txt | 245 | 1792006132000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM008.txt | DM008.txt | 305 | 1792006133000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM009.txt | DM009.txt | 252 | 1792006133000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM010.txt | DM010.txt | 251 | 1792006134000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM011.txt | DM011.txt | 309 | 1792006134000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM012.txt | DM012.txt | 266 | 1792006134000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM013.txt | DM013.txt | 244 | 1792006135000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM014.txt | DM014.txt | 276 | 1792006135000 |
| /Volumes/cs_genie_research_catalog/ad_sales/deal_memory/DM015.txt | DM015.txt | 287 | 1792006135000 |

**Embedding endpoint `databricks-bge-large-en` live** — returned a 1024-dim vector.
