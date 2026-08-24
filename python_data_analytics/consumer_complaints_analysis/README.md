# Consumer Complaint Intelligence

A portfolio capstone project analyzing the U.S. CFPB Consumer Complaint Database to understand complaint volume, product risk, institutional concentration, and customer experience outcomes across financial services.

This project turns a large public complaints dataset into an analytical narrative grounded in real-world regulatory and customer signals. It is built for exploratory analysis, reproducible research, and stakeholder-friendly visual reporting.

## Project purpose

The analysis answers questions such as:

- Which companies receive the highest complaint volumes?
- Which products and issues generate the most pressure on consumers?
- How have complaint patterns shifted over time?
- What do complaint-resolution outcomes look like across firms and product categories?
- Which institutions show the strongest or weakest operational handling?

## Dataset

Source: CFPB Consumer Complaint Database

- Approx. 1.28 million complaints
- Roughly 5,275 companies represented
- Time range: Dec 2011 to May 2019
- Data source: https://www.kaggle.com/datasets/selener/consumer-complaint-database

Important:

- The raw dataset is not committed to this repository.
- Download the Kaggle file locally and place it in `data/rows.csv` or a similar local path.
- Update the notebook `DATA_PATH` variable to your local CSV path before running the analysis.

## Project structure

```text
consumer_complaints_analysis/
├── README.md
├── .gitignore
├── requirements.txt
├── data/
│   └── README.md
├── notebooks/
│   ├── CFPB_V2.ipynb
│   └── Consumer-Complaints_DA.ipynb
├── reports/
│   └── README.md
├── src/
│   └── README.md
└── outputs/   (optional, for cleaned data or exported charts)
```

## Notebook overview

### `notebooks/CFPB_V2.ipynb`
A more polished, consolidated analytical notebook with an end-to-end story from dataset profiling through market concentration, operational performance, complaint outcomes, and a bureau accountability lens.

### `notebooks/Consumer-Complaints_DA.ipynb`
A broader exploratory notebook that walks through the core data profiling, cleaning, and analytical narrative using Python, pandas, and visualization libraries.

## Tools and stack

- Python 3
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Plotly
- Jupyter Notebook

## Setup

1. Open the project folder.
2. Create a virtual environment if desired.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Download the CFPB file from Kaggle and place it in the local `data` folder.
5. Update the `DATA_PATH` variable in the notebook to the correct CSV location.
6. Run the notebooks in Jupyter or VS Code Notebook mode.

## Recommended workflow

- Use the notebooks as the primary analysis environment.
- Store cleaned datasets or exports in a future `outputs/` directory.
- Keep final presentation materials in `reports/`.
- Add reusable functions under `src/` when the analysis is refactored for reuse.

## Business value

This project demonstrates how large-scale public complaint data can be used to:

- identify systemic financial product risk
- benchmark company performance against a broad market baseline
- quantify complaint concentration and operational quality
- transform raw consumer signals into a decision-ready analytical story

## Notes

The project is intentionally focused on exploratory and descriptive analysis rather than production ML deployment. It is best used as a strong analytics and storytelling capstone grounded in real regulatory data.
