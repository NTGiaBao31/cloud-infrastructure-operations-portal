from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.validation import (
    NAME_RE,
    TOKEN_RE,
    valid_azure_resource_id,
    valid_hostname,
    valid_ip,
    valid_monitoring_target,
)

OS_CHOICES = [("linux", "Linux"), ("windows", "Windows")]
STATUS_CHOICES = [
    ("online", "Online"),
    ("warning", "Warning"),
    ("down", "Down"),
    ("maintenance", "Maintenance"),
    ("unknown", "Unknown"),
]
ACTION_CHOICES = [
    ("restart_service", "Restart service"),
    ("restart_container", "Restart container"),
    ("disk_cleanup", "Disk cleanup (dry-run)"),
]


def _token(value, message):
    if value and not TOKEN_RE.match(value):
        raise ValidationError(message)


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Sign in")


class ServerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    hostname = StringField("Hostname", validators=[DataRequired(), Length(max=255)])
    ip_address = StringField("IP address", validators=[DataRequired(), Length(max=45)])
    environment = StringField("Environment", validators=[DataRequired(), Length(max=40)])
    os_type = SelectField("OS", choices=OS_CHOICES, validators=[DataRequired()])
    status = SelectField("Status", choices=STATUS_CHOICES, validators=[DataRequired()])
    monitoring_target = StringField("Monitoring target", validators=[Optional(), Length(max=255)])
    automation_group = StringField("Automation group", validators=[Optional(), Length(max=120)])
    azure_resource_id = StringField("Azure resource ID", validators=[Optional(), Length(max=512)])
    submit = SubmitField("Save server")

    def validate_name(self, field):
        if not NAME_RE.match(field.data.strip()):
            raise ValidationError("Use letters, numbers, dots, underscores, or hyphens.")

    def validate_hostname(self, field):
        if not valid_hostname(field.data):
            raise ValidationError("Enter a valid hostname.")

    def validate_ip_address(self, field):
        if not valid_ip(field.data):
            raise ValidationError("Enter a valid IP address.")

    def validate_environment(self, field):
        if not TOKEN_RE.match(field.data.strip()) or len(field.data.strip()) > 40:
            raise ValidationError("Use a short environment token such as prod or staging.")

    def validate_monitoring_target(self, field):
        if not valid_monitoring_target(field.data):
            raise ValidationError("Enter a hostname or hostname:port.")

    def validate_automation_group(self, field):
        _token(field.data.strip(), "Use a short group token.")

    def validate_azure_resource_id(self, field):
        if not valid_azure_resource_id(field.data):
            raise ValidationError("Enter an Azure resource ID without spaces.")


class JobForm(FlaskForm):
    server_id = SelectField("Server", coerce=int, validators=[DataRequired()])
    action_key = SelectField("Action", choices=ACTION_CHOICES, validators=[DataRequired()])
    service_name = StringField("Service name", validators=[Optional(), Length(max=128)])
    container_name = StringField("Container name", validators=[Optional(), Length(max=128)])
    path = StringField("Path token", validators=[Optional(), Length(max=128)])
    simulate = SelectField(
        "Mock result",
        choices=[("success", "Success"), ("fail", "Simulated failure")],
        default="success",
        validators=[Optional()],
    )
    submit = SubmitField("Run action")
