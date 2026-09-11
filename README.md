# Kaustubh Patil . Jarvis Consulting

Machine Learning Engineer at Jarvis Consulting with six years of experience building data and ML systems on Databricks, Azure, and GCP. At Gartner (Talent Neuron) I built the Databricks and PySpark ETL workflows that turned large-scale workforce data into labour market research, along with the dashboards analysts and clients read it through. Outside of client work I publish the tooling I wish existed: agentnorm, a zero-dependency behavioural monitor for AI agents, and a Buhlmann credibility study across roughly 40,000 agent episodes, both shipped on PyPI. My deep learning capstones turn models into decisions, pricing a credit scorecard at 578M dollars of net benefit and showing how an equity signal's ranking inverts once realistic trading costs are charged. What interests me most is the part after the model works: calibration, leakage, drift, and pipelines that stay honest in production.

## Skills

**Proficient:** Python (OOP), SQL, PySpark / Apache Spark, Databricks, Pandas / NumPy, scikit-learn, ETL/ELT Pipeline Design, Azure (Databricks, ADF, AKS), PostgreSQL, Docker, Git, Linux/Bash

**Competent:** PyTorch, Deep Learning (CNN, LSTM, Transfer Learning), SHAP / Model Explainability, MLflow, Model Deployment & Drift Detection, Delta Lake / Medallion Architecture, Apache Airflow, CI/CD (GitHub Actions), System Design & UML, REST APIs / Microservices, AWS (EC2, S3, VPC, IAM), GCP (Vertex AI, BigQuery, GKE)

**Familiar:** Power BI / DAX, RAG Pipelines (LangChain, LangGraph, LLM Evals), Kubernetes (AKS/GKE), Terraform, ArgoCD (GitOps), Scala, Apache Kafka, Snowflake, MongoDB / Cassandra, Prometheus / Grafana

## Jarvis Projects

Project source code: [https://github.com/jarviscanada/jarvis_data_eng_Patil](https://github.com/jarviscanada/jarvis_data_eng_Patil)


**Cluster Monitor** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/linux_sql)]: Implemented a Linux Cluster Monitoring Agent in Bash that collects hardware specifications and real-time resource usage from CentOS nodes and persists them to a centralized PostgreSQL database provisioned with Docker. Automated recurring collection through crontab, handled host registration and duplicate-node edge cases, and wrote SQL analytical queries that surface per-host utilization trends for capacity planning. Version-controlled the agent with Git and documented setup so system administrators can reproduce the deployment on any node in the cluster.

**SQL Data Analytics** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/sql)]: Practiced production SQL against a PostgreSQL database modelling a sports club management system of members, facilities, and booking records, provisioned in Docker. Wrote queries covering DDL and DML, multi-table joins, aggregations, subqueries, string functions, date arithmetic, and window functions, and reviewed the schema against 1NF, 2NF, and 3NF normalization rules. Validated every result against expected output using the psql CLI and DBeaver, and documented each exercise so the query patterns stay reusable.

**Python Data Analytics** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/python_data_analytics)]: Delivered two end-to-end Python analytics projects. The first profiles the U.S. CFPB Consumer Complaint Database (1.28M complaints, 5,275 firms, 2011-2019) with Pandas, engineering time-series, lag, and company-tier features, then reports market concentration, product mix shift, and a multi-dimension accountability scorecard through Plotly. The second loads London Gift Shop retail transactions into a PostgreSQL warehouse and analyzes monthly sales, cancellations, customer lifecycle, and RFM segmentation in Jupyter, publishing the findings as an HTML dashboard for stakeholders.

**Databricks Spark Analytics** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/Databricks_Spark)]: Built two Databricks Lakehouse pipelines on the Bronze, Silver, and Gold medallion pattern using PySpark and Delta Lake. The fraud platform ingests transaction, card, user, and label data from SQL Server and Azure Storage, standardizes and enriches it, and publishes Gold fraud KPIs alongside a Random Forest credit-risk classifier. The market platform ingests the Twelve Data API through a Delta Live Tables pipeline, applies short, medium, and long window trend analysis, and governs the published tables with Unity Catalog for dashboarding.

**Credit Scoring Decision System** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/credit_scoring)]: Built an end-to-end consumer credit scoring system on 307,511 Home Credit applications and 1.7M credit-bureau records, reaching 0.774 test AUROC and converting it into a decision rule worth $578.7M net on the sealed test book. Priced every possible approval rate with a profit curve, verified calibration decile by decile instead of class weighting, mapped all 279 features to lawful adverse-action reasons, and test-fired the PSI drift alarm under a simulated recession. A fairness audit found gender among the model inputs and removed it for 0.0006 AUROC.

**Deep Learning Equity Signal** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/equity_signal)]: Benchmarked feedforward, LSTM, CNN, and transfer-learning models against a systematic desk's incumbent signal across 48 S&P 500 stocks and 259,073 rows, then charged realistic 10bps trading costs, which inverted the ranking: the incumbent's 159x annual turnover turned a positive gross Sharpe into -0.30 net. Proved leak-freedom by recomputation rather than assertion, fixed an honest accuracy ceiling from return autocorrelation before modeling, and recommended iterating rather than deploying because the best network still lost to equal-weight buy-and-hold.

**Core Java Apps** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/core_java)]: Not Started

**Spring RESTful Microservices App** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/springboot)]: Not Started

**JavaScript** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/javascript)]: Not Started

**Cloud/DevOps** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/cloud_devops)]: Not Started


## Highlighted Projects
**Agent Credibility: Actuarial Pricing for AI Agent Deployments** [[GitHub](https://github.com/kaustubhspatil/agent-credibility)]: Tested whether a pooled Buhlmann credibility prior can price AI agent deployments, across three corpora and roughly 40,000 episodes, with 192 tests and every negative control reported. Replicated the governing constant K on two independent corpora sharing no code path (7.6 and 7.0), establishing it as a property of the agent's role rather than an artifact of one dataset. Shipped the result as a PyPI SDK talking to a live bureau service over TLS, and published a downward correction to an early headline finding when a larger corpus contradicted it.

**agentnorm: Behavioural Monitoring for AI Agents** [[GitHub](https://github.com/kaustubhspatil/agentnorm)]: Published a zero-dependency Python package that monitors how an AI agent behaves at runtime, as opposed to grading offline what it said. Records tool calls, scopes, and result sizes, then flags runs that do not resemble prior benign ones with an explainable verdict. Designed the API to wrap existing tool callables without restructuring or context propagation, and made the anomaly detection cold-start safe so a new agent version is usable before it has history.

**Biological Network Analysis & Protein Kinase Inhibition in Breast Cancer** [[GitHub](https://scholar.google.ca/citations?view_op=view_citation&hl=en&user=Gt5kbUMAAAAJ&citation_for_view=Gt5kbUMAAAAJ:u5HHmVD_uO8C)]: Led a peer-reviewed bioinformatics study on protein kinase inhibition networks in breast cancer. Designed the experimental approach, performed network analysis on protein interaction data, validated findings against published literature, and authored the manuscript as lead author through to publication.


## Professional Experiences

**Machine Learning Engineer, Jarvis Consulting (Apr 2026 - Present)**: Design, deliver, and maintain secure, high-performance ML data pipelines using Python, PySpark, and cloud-native technologies for banking and financial services clients. Document service architecture with UML sequence and component diagrams so backend designs are reviewable before implementation, and streamline ETL and analytics workflows on cloud platforms. Build production-grade Linux, SQL, Python, and Spark projects with Git, Docker, and CI/CD while working in an agile team with peer code review.

**AI/ML Research Engineer, Gartner (Talent Neuron) (Sept 2023 - Dec 2025)**: Developed ETL workflows on Databricks and Microsoft Azure using Python and Spark, turning large-scale raw workforce datasets into the clean, queryable tables behind Talent Neuron's labour market research. Built and maintained the extraction and transformation pipelines feeding recurring research deliverables, and designed the dashboards and reporting layer that made skills demand, talent supply, and hiring trends legible to analysts and clients. Supported model retraining and scheduled orchestration for the research products, and worked directly with analysts to turn open research questions into reproducible datasets they could interrogate themselves.

**Data Engineer, IPLIX Media (Jan 2022 - Dec 2023)**: Built and maintained real-time analytics pipelines in Python and SQL to process high-volume YouTube and social media data, and delivered the Power BI dashboards and reporting layer on top of them. Designed data-processing workflows that extracted quantitative insights from unstructured content to support creator and campaign decisions. Implemented automated unit and integration tests inside CI/CD pipelines so data regressions were caught before release.

**Data Engineer, Mosil Lubricant (Aug 2020 - Jan 2022)**: Designed and implemented automated ETL pipelines in Python and SQL that consolidated disparate company data into a centralized warehouse, replacing manual consolidation work. Engineered SQL queries for data mining and analytics, establishing reliable and reusable datasets for downstream applications. Built executive-facing Power BI dashboards covering cost, supply, and operational KPIs, and partnered with business stakeholders to translate reporting requirements into maintainable data models.


## Education
**York University (Sept 2025)**, Diploma, Cloud Operations

**Conestoga College of Technology (Sept 2024)**, Diploma, Big Data Solutions Architecture

**Dr. D. Y. Patil University (Jul 2023)**, Bachelor of Technology, Data Science and Bioinformatics
- GPA 4.0, with A+ standing across Data Science and Bioinformatics coursework
- Lead author, peer-reviewed publication: Biological Network Analysis & Protein Kinase Inhibition in Breast Cancer


## Miscellaneous
- AWS Certified Solutions Architect - Associate
- Oracle Cloud Infrastructure 2025 Certified Application Integration Professional
- Author of agentnorm and freeboard, two open-source Python packages published on PyPI
- I watch speedruns of games I have never played. Optimization as a spectator sport.