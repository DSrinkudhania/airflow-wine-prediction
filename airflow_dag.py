from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import timedelta
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'mlflow_deployment_dag',
    default_args=default_args,
    description='DAG for MLflow Flask application deployment',
    schedule_interval=timedelta(days=1),  # Set the schedule as needed
    start_date=days_ago(1),
    catchup=False,  # Do not backfill DAG runs
)

# Define the BashOperator to create the BuildConfig in OpenShift
create_build_config_task = BashOperator(
    task_id='create_build_config',
    bash_command='oc apply -f buildconfig.yaml',
    dag=dag,
)

# Define the BashOperator to start the build process in OpenShift
start_build_task = BashOperator(
    task_id='start_build',
    bash_command='oc start-build mlflow-wine-prediction-build',
    dag=dag,
)

# Define the BashOperator to deploy the application to OpenShift
deploy_task = BashOperator(
    task_id='deploy_to_openshift',
    bash_command='oc apply -f deploymentconfig.yaml',
    dag=dag,
)

# Define the task dependencies
create_build_config_task >> start_build_task >> deploy_task
