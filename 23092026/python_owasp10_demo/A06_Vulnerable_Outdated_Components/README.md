### Security Best Practices

It is important to regularly check for outdated or vulnerable dependencies in your Python project.  
One recommended tool is **pip-audit**, which scans your environment and reports known security vulnerabilities.

#### Installing pip-audit
```bash
pip install pip-audit
```

#### Running pip-audit
To check for vulnerabilities in your installed packages:
```bash
pip-audit
```

To check for vulnerabilities in a `requirements.txt` file:
```bash
pip-audit -r requirements.txt
```

#### Sample Output
```text
Found 2 known vulnerabilities in 1 package
Name    Version  ID             Fix Versions
------  -------  -------------  ------------
flask   0.5      PYSEC-2019-179 1.0
flask   0.5      PYSEC-2018-66  0.12.3
```

#### Recommendations
- Always update the reported vulnerable packages to the latest secure version.
- Re-run `pip-audit` after updates to confirm all vulnerabilities are resolved.
- Integrate `pip-audit` into your CI/CD pipeline to ensure dependencies remain secure over time.
