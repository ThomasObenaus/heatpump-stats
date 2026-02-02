FROM grafana/grafana:12.3

# Switch to root to copy files and set permissions
USER root

# Copy provisioning configurations
COPY provisioning /etc/grafana/provisioning

# Ensure proper permissions
RUN chown -R grafana:root /etc/grafana/provisioning

# Switch back to grafana user
USER grafana
