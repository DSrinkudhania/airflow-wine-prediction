from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.kubernetes_pod_operator import KubernetesPodOperator
from datetime import timedelta
from airflow.utils.dates import days_ago
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the Airflow DAG
default_args = {
    'owner': 'rinku.dhanai@gmail.com',
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

# Custom Python function to add an entry to the database
@task
def add_entry_to_db():
    # Connect to the database
    db_url = Variable.get("db_connection_url")  
    engine = create_engine(db_url)
    Base = declarative_base()
    
    class MyTable(Base):
        __tablename__ = 'my_table'
        id = Column(Integer, primary_key=True)
        name = Column(String(255))

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Add an entry to the database
    new_entry = MyTable(name="build_deplot")
    session.add(new_entry)
    session.commit()
    session.close()

# Define the KubernetesPodOperator to create the BuildConfig in OpenShift
create_build_config_task = KubernetesPodOperator(
    task_id='create_build_config',
    name='create-build-config-pod',
    image='openshift/origin-cli',  # Using the OpenShift CLI image
    cmds=["sh", "-c", "oc apply -f buildconfig.yaml"],  # oc apply command to create the BuildConfig
    dag=dag,
)

# Define the KubernetesPodOperator to start the build process in OpenShift
start_build_task = KubernetesPodOperator(
    task_id='start_build',
    name='start-build-pod',
    image='openshift/origin-cli',  # Using the OpenShift CLI image
    cmds=["sh", "-c", "oc start-build mlflow-wine-prediction-build"],  # oc start-build command
    dag=dag,
)

# Define the KubernetesPodOperator to deploy the application to OpenShift
deploy_task = KubernetesPodOperator(
    task_id='deploy_to_openshift',
    name='deploy-pod',
    image='openshift/origin-cli',  # Using the OpenShift CLI image
    cmds=["sh", "-c", "oc apply -f deploymentconfig.yaml"],  # oc apply command to deploy the application
    dag=dag,
)

# Define the task dependencies
create_build_config_task >> start_build_task >> deploy_task >> add_entry_to_db()
