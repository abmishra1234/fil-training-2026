# Troubleshooting: symptom -> cause -> fix

| Symptom (where) | Likely cause | Fix |
|---|---|---|
| `port is already allocated` (compose up) | 8080 in use | stop the other app, or map `"8081:8080"` and use localhost:8081 |
| `python3: not found` (Setup) | not on the lab image | `docker compose up -d --build` in `00-jenkins-setup` |
| pip timeout / connection error (Setup) | container has no internet / proxy | Docker Desktop -> Settings -> Resources -> Proxies; test `docker exec fil-jenkins curl -sI https://pypi.org` |
| `Failed to connect to repository` (job config) | URL typo, private repo, no internet | `docker exec fil-jenkins git ls-remote https://github.com/<you>/expense-api.git` |
| Jenkinsfile not found | file name/case, branch, Script Path | `Jenkinsfile` in repo root, Branch `*/main` |
| `F401 ... imported but unused` (Lint) | real lint error | fix the line; locally `ruff check --fix` |
| `No test report files were found` | junit path differs from `--junitxml` path | use `reports/junit.xml` in both |
| `Could not find credentials entry with ID` | ID typo / created in a folder | Global credential with ID `expense-jwt-secret` |
| `JWT_SECRET is not set` (Deploy) | withCredentials missing / wrong variable | `variable: 'JWT_SECRET'` |
| `SMOKE FAIL service is listening` | app refused to start | `docker exec fil-jenkins tail /var/jenkins_home/staging/expense-api/app.log` (look for `config_error`) |
| App gone after container restart | the app is a process in the container | run the pipeline again |
| `No library named fil-jenkins-lib` | not registered / name typo | Manage Jenkins -> System -> Global Trusted Pipeline Libraries |
| `No such DSL method 'pythonPipeline'` | file not in `vars/` or wrong case | `vars/pythonPipeline.groovy`, push |
| cannot resolve `v1.0.0` | tag not pushed / tags not discovered | `git push origin v1.0.0`; add Behaviour "Discover tags" |
| `Unable to resolve action <you>/python-ci-action@v1` | placeholder not replaced, private repo, missing tag | public repo, `git push origin --tags` |
| GitHub asks for password on push | passwords not accepted | Git Credential Manager browser login, or fine-grained token (Contents: read/write) |
