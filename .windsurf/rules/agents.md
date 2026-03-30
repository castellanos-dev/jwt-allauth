---
trigger: always_on
---
# Environment & Execution Rules

## Python Environment: 'jwt-allauth'
This project strictly requires the Conda environment named `jwt-allauth`.

### Critical Terminal Instructions
1. **Mandatory Activation**: NEVER execute `python`, `pip`, or test scripts without ensuring the `jwt-allauth` environment is active.
2. **Execution Strategy (Chaining)**: To guarantee the environment is loaded, **always chain the activation** with the command using the `&&` operator.

   - ❌ **Incorrect**:
     ```
     conda activate jwt-allauth
     # (Sending this, then trying to run the script in a separate turn)
     python main.py
     ```

   - ✅ **Correct (Always do this)**:
     ```
     conda activate jwt-allauth && python main.py
     ```
     ```
     conda activate jwt-allauth && pip install pandas
     ```

3. **Error Handling**: If you encounter a `ModuleNotFoundError`, assume immediately that you forgot to activate `jwt-allauth`. Do not attempt to reinstall libraries; simply re-run the command with the proper activation.
