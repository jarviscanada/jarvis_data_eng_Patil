# Kaustubh Patil . Jarvis Consulting

Machine Learning Engineer at Jarvis Consulting with five years of experience building secure, high-performance data and ML pipelines on Azure, Databricks, and GCP. At Gartner (Talent Neuron) I developed Databricks and PySpark workflows over large-scale workforce datasets, supported Azure ETL, model retraining, and orchestration, and maintained RESTful microservices and CI/CD for ML delivery. I am an AWS Certified Solutions Architect - Associate and work daily in Python, SQL, Spark, Docker, Kubernetes, and Terraform, with growing depth in MLOps governance and GenAI patterns such as RAG pipelines and LLM evaluation. What excites me about this industry is the engineering craft behind ML: clean interfaces, documented designs, observability, and pipelines that stay reliable in production. I am now applying that foundation to banking and financial services work at Jarvis.

## Skills

**Proficient:** Python (OOP), SQL, PySpark / Apache Spark, Databricks, Azure (Databricks, ADF, AKS), ETL/ELT Pipeline Design, PostgreSQL, Docker, Git, Linux/Bash, CI/CD (GitHub Actions), Agile/Scrum

**Competent:** Kubernetes (AKS/GKE), Terraform, ArgoCD (GitOps), Apache Airflow, MLflow, Model Deployment & Drift Detection, REST APIs / Microservices, System Design & UML, AWS (EC2, S3, VPC, IAM), GCP (Vertex AI, BigQuery, GKE), Power BI / DAX, RAG Pipelines (LangChain, LangGraph, LLM Evals)

**Familiar:** Scala, Apache Kafka, Snowflake, Elasticsearch / OpenSearch, MongoDB, Cassandra, Prometheus / Grafana, New Relic / ELK-EFK, Moogsoft

## Jarvis Projects

Project source code: [https://github.com/jarviscanada/jarvis_data_eng_Patil](https://github.com/jarviscanada/jarvis_data_eng_Patil)


**Cluster Monitor** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/linux_sql)]: Implemented a Linux Cluster Monitoring Agent in Bash that collects hardware specifications and real-time resource usage from CentOS nodes and persists them to a centralized PostgreSQL database provisioned with Docker. Automated recurring collection through crontab, handled host registration and duplicate-node edge cases, and wrote SQL analytical queries that surface per-host utilization trends for capacity planning. Version-controlled the agent with Git and documented setup so system administrators can reproduce the deployment on any node in the cluster.

**SQL Data Analytics** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/sql)]: Practiced production SQL against a PostgreSQL database modelling a sports club management system of members, facilities, and booking records, provisioned in Docker. Wrote queries covering DDL and DML, multi-table joins, aggregations, subqueries, string functions, date arithmetic, and window functions, and reviewed the schema against 1NF, 2NF, and 3NF normalization rules. Validated every result against expected output using the psql CLI and DBeaver, and documented each exercise so the query patterns stay reusable.

**Python Data Analytics** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/python_data_analytics)]: Delivered two end-to-end Python analytics projects. The first profiles the U.S. CFPB Consumer Complaint Database (1.28M complaints, 5,275 firms, 2011-2019) with Pandas, engineering time-series, lag, and company-tier features, then reports market concentration, product mix shift, and a multi-dimension accountability scorecard through Plotly. The second loads London Gift Shop retail transactions into a PostgreSQL warehouse and analyzes monthly sales, cancellations, customer lifecycle, and RFM segmentation in Jupyter, publishing the findings as an HTML dashboard for stakeholders.

**Databricks Spark Analytics** [[GitHub](https://github.com/jarviscanada/jarvis_data_eng_Patil/tree/master/Databricks_Spark)]: Built two Databricks Lakehouse pipelines on the Bronze, Silver, and Gold medallion pattern using PySpark and Delta Lake. The fraud platform ingests transaction, card, user, and label data from SQL Server and Azure Storage, standardizes and enriches it, and publishes Gold fraud KPIs alongside a Random Forest credit-risk classifier. The market platform ingests the Twelve Data API through a Delta Live Tables pipeline, applies short, medium, and long window trend analysis, and governs the published tables with Unity Catalog for dashboarding.


## Highlighted Projects
**Scalable VPC Architecture on AWS** [[GitHub](https://github.com/kaustubhspatil/Scalability-of-VPC-Architecture-on-AWS)]: Designed and deployed a modular, scalable, and secure virtual network on AWS using Amazon VPC. Implemented public and private subnets across multiple availability zones, configured NAT gateways, route tables, and security groups, and applied infrastructure-as-code principles so the production-ready network foundation can be provisioned repeatably. Reinforced the architecture patterns covered by the AWS Solutions Architect - Associate certification.

**CI/CD Automation with DevOps Tools** [[GitHub](https://github.com/kaustubhspatil/CI-CD-Automation-with-DevOps-Tools)]: Built a fully automated end-to-end CI/CD pipeline integrating Jenkins for orchestration, SonarQube for static code analysis, JFrog Artifactory for artifact management, and Docker with Kubernetes for containerized deployment. Instrumented the pipeline with Prometheus and Grafana for build-health monitoring and alerting, demonstrating a production-grade DevOps workflow from commit to deployment.

**Biological Network Analysis & Protein Kinase Inhibition in Breast Cancer** [[GitHub](https://scholar.google.ca/citations?view_op=view_citation&hl=en&user=Gt5kbUMAAAAJ&citation_for_view=Gt5kbUMAAAAJ:u5HHmVD_uO8C)]: Led a peer-reviewed bioinformatics study on protein kinase inhibition networks in breast cancer. Designed the experimental approach, performed network analysis on protein interaction data, validated findings against published literature, and authored the manuscript as lead author through to publication.


## Professional Experiences

**Machine Learning Engineer, Jarvis Consulting (Jan 2026 - Present)**: Design, deliver, and maintain secure, high-performance ML data pipelines using Python, PySpark, and cloud-native technologies for banking and financial services clients. Document service architecture with UML sequence and component diagrams so backend designs are reviewable before implementation, and streamline ETL and analytics workflows on cloud platforms. Build production-grade Linux, SQL, Python, and Spark projects with Git, Docker, and CI/CD while working in an agile team with peer code review.

**Data and Research Engineer (AI/ML Platform), Gartner (Talent Neuron) (Sept 2023 - Dec 2025)**: Developed data workflows on Databricks and Microsoft Azure using Python and Spark to process large-scale workforce datasets powering AI/ML products. Supported Azure-based ETL, data extraction, model retraining, and workflow orchestration across the model lifecycle. Built and maintained RESTful microservices for internal data workflows using Python and cloud-native patterns, and contributed to CI/CD implementation for ML and data pipelines, enabling reliable deployment and consistent production processes across teams.

**Data Engineer, IPLIX Media (Jan 2022 - Sept 2023)**: Built and maintained real-time analytics pipelines in Python and SQL to process high-volume YouTube and social media data, and delivered the Power BI dashboards and reporting layer on top of them. Designed data-processing workflows that extracted quantitative insights from unstructured content to support creator and campaign decisions. Implemented automated unit and integration tests inside CI/CD pipelines so data regressions were caught before release.

**Data Engineer, Mosil Lubricant (Aug 2021 - Feb 2022)**: Designed and implemented automated ETL pipelines in Python and SQL that consolidated disparate company data into a centralized warehouse, replacing manual consolidation work. Engineered SQL queries for data mining and analytics, establishing reliable and reusable datasets for downstream applications. Built executive-facing Power BI dashboards covering cost, supply, and operational KPIs, and partnered with business stakeholders to translate reporting requirements into maintainable data models.


## Education
**York University (Sept 2025)**, Diploma, Cloud Operations

**Conestoga College of Technology (Sept 2024)**, Diploma, Big Data Solutions Architecture

**Dr. D. Y. Patil University (Jul 2023)**, Bachelor of Technology, Data Science and Bioinformatics
- GPA 4.0, with A+ standing across Data Science and Bioinformatics coursework
- Lead author, peer-reviewed publication: Biological Network Analysis & Protein Kinase Inhibition in Breast Cancer


## Miscellaneous
- AWS Certified Solutions Architect - Associate
- Oracle Cloud Infrastructure 2025 Certified Application Integration Professional
- Building Databricks and MLOps side projects in financial risk and market analytics
- Open-source contributor in MLOps and GenAI tooling