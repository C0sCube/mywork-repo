from django.urls import path
from . import views

urlpatterns = [
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("auth-check", views.auth_check, name="auth_check"),
    path("", views.dashboard, name="dashboard"),
    path("dashboard", views.dashboard, name="dashboard_page"),
    path("status_data", views.status_data, name="status_data"),
    path("viewer/pdf/<str:filename>", views.view_pdf, name="view_pdf"),
    path("dash_csv", views.dash_csv, name="dash_csv"),
    path("apply_csv", views.apply_csv, name="apply_csv"),
    path("download_dashboard_json/<str:filename>", views.download_dashboard_json, name="download_dashboard_json"),
    path("upload", views.upload_files, name="upload_files"),
    path("reprocess/<int:job_id>", views.reprocess, name="reprocess"),
    path("push_job/<int:job_id>", views.push_job, name="push_job"),
    
    #config editor paths
    path("config-editor", views.config_editor, name="config_editor"),
    path("list-files/<str:year>", views.list_files, name="list_files"),
    path("years", views.get_years, name="years"),
    path("load-config", views.load_config, name="load_config"),
    path("save-config", views.save_config, name="save_config"),
    path("backup-config", views.backup_config, name="backup_config"),
    path("create-config", views.create_config, name="create_config"),
    path("delete-config", views.delete_config, name="delete_config"),
    path("csv-to-json", views.csv_to_json, name="csv_to_json"),
    path("convert_csv", views.convert_csv, name="convert_csv"),
    path("convert_json", views.convert_json, name="convert_json"),
    path("download_csv/<str:filename>", views.download_csv, name="download_csv"),
    path("download_pipeline_json/<str:filename>", views.download_pipeline_json, name="download_pipeline_json"),
    path("cleanup_pipeline", views.cleanup_pipeline, name="cleanup_pipeline"),
    path("viewer/json/<str:source>/<str:filename>", views.view_json, name="view_json"),
    path("push_json_sp", views.push_json_sp, name="push_json_sp"),
    
    #sidkim paths
    path("sid-data", views.sid_data, name="sid_data"),
    path("upload-sid-kim", views.upload_sid_kim, name="upload_sid_kim"),
    
    #logging paths
    path("daily-log", views.daily_logs, name="daily_logs"),
    path("load-daily-log", views.load_daily_log, name="load_daily_log"),
    path("files/json/", views.list_json_files, name="list_json_files"),
    path("files/json/<str:filename>", views.serve_json_files, name="serve_json_files"),
    path("files/xlsx/", views.list_csv_files, name="list_csv_files"),
    path("files/xlsx/<str:filename>", views.serve_csv_files, name="serve_csv_files"),
    path("amc-data", views.amc_data, name="amc_data"),
    path("company_registry", views.company_registry, name="company_registry"),
    path("amc_data_registry", views.amc_data_registry, name="amc_data_registry"),
    path("json_list", views.json_list, name="json_list"),
    # path("logo/<int:logo_id>", views.get_logo, name="get_logo"),
    
    path("validate-data", views.validate_data, name="validate_data"),
]
