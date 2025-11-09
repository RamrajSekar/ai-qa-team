###Activate poetry
py -m poetry env activate

###Deactivate
deactivate

Start Backend
cd ai-qa-team-api
py -m poetry run uvicorn app.main:app --reload

##Redis is only useful once you start adding background jobs, caching, and async test-execution orchestration.
