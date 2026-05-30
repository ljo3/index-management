# Portfolio construction in the context of financial index management #

To get started:
1. Clone the repo  
   `git clone https://github.com/ljon3/index-management.git`  
   `cd index-management`

2. Create a virtual environment and install dependencies using [uv](https://github.com/astral-sh/uv):  
   `uv venv`  
   `uv pip install -r requirements.txt`

3. Activate the environment and set PYTHONPATH to the repo root:  
   `source .venv/bin/activate`  
   `export PYTHONPATH=$(pwd)`

Workflows included in this repo:  

* ## Workflow 1: Portfolio construction ##  
  Start with the end-to-end demo notebook at the repo root:  
  `driver.ipynb`  

  Detailed per-module notebooks are in `index_management/drivers/`:  
  `index_management/drivers/driver-strategy.ipynb`  
  `index_management/drivers/driver-market.ipynb`  
  `index_management/drivers/driver-universe.ipynb`  
  `index_management/drivers/driver-valuation.ipynb`  

  The portfolio can also be explored interactively via the Streamlit app:  
  `streamlit run app_portfolio_visualize.py`  
  access the app by navigating to the address:  
  `http://localhost:8501`  
  Verify this is the port displayed when you run the   
  `streamlit run app_portfolio_visualize.py` 

* ## Workflow 2: Unit Testing ##  
  An integral part of development workflows is testing. I have setup tests in the respective folders. To run the tests, execute:  
  `pytest`

* ## Workflow 3: Automation Workflows for CI/CD ##  
  Daily valuation is automated via Github Actions, configured in:  
  `.github/workflows/valuation.yml`  
  The script it runs is `.github/scripts/value_daily.py`.  
  This can be visualized at: https://github.com/ljon3/index-management/actions
