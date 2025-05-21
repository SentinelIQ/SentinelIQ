from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from organizations.models import Organization


User = get_user_model()


class ThreatIntelligenceFeed(models.Model):
    """Modelo base para feeds de Threat Intelligence"""
    
    TYPE_CHOICES = (
        ('misp', 'MISP'),
        ('otx', 'AlienVault OTX'),
        ('threatfox', 'ThreatFox'),
        ('virustotal', 'VirusTotal'),
        ('custom', 'Custom Feed'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
        ('pending', 'Pending Configuration'),
    )
    
    name = models.CharField(_("Feed Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    feed_type = models.CharField(_("Feed Type"), max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="threat_feeds",
        verbose_name=_("Organization")
    )
    is_public = models.BooleanField(_("Public Feed"), default=False, 
                                    help_text=_("If checked, this feed will be available to all organizations"))
    last_sync = models.DateTimeField(_("Last Synchronization"), null=True, blank=True)
    sync_frequency = models.IntegerField(_("Sync Frequency (minutes)"), default=60)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    
    class Meta:
        verbose_name = _("Threat Intelligence Feed")
        verbose_name_plural = _("Threat Intelligence Feeds")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_feed_type_display()})"


class MISPInstance(ThreatIntelligenceFeed):
    """Configuração de instância MISP"""
    
    url = models.URLField(_("MISP URL"), help_text=_("URL of the MISP instance"))
    api_key = models.CharField(_("API Key"), max_length=255)
    verify_ssl = models.BooleanField(_("Verify SSL"), default=True)
    
    # Filter settings
    import_events = models.BooleanField(_("Import Events"), default=True)
    import_attributes = models.BooleanField(_("Import Attributes"), default=True)
    import_from_days = models.IntegerField(_("Import from last X days"), default=30)
    import_tags = models.BooleanField(_("Import Tags"), default=False, 
                                     help_text=_("Import all tag definitions from MISP"))
    import_galaxies = models.BooleanField(_("Import Galaxies/Clusters"), default=False,
                                         help_text=_("Import all galaxy and cluster definitions from MISP"))
    
    # Filters for specific tags or event types
    tags_to_include = models.TextField(_("Tags to Include"), blank=True,
                                      help_text=_("Comma-separated list of tags to include"))
    tags_to_exclude = models.TextField(_("Tags to Exclude"), blank=True,
                                      help_text=_("Comma-separated list of tags to exclude"))
    
    class Meta:
        verbose_name = _("MISP Instance")
        verbose_name_plural = _("MISP Instances")
    
    def __str__(self):
        return f"MISP: {self.name} ({self.url})"


class ThreatIntelligenceItem(models.Model):
    """Modelo para armazenar itens de inteligência obtidos dos feeds"""
    
    TYPE_CHOICES = (
        ('ip', 'IP Address'),
        ('domain', 'Domain'),
        ('url', 'URL'),
        ('hash', 'File Hash'),
        ('email', 'Email'),
        ('event', 'Event'),
        ('other', 'Other'),
    )
    
    feed = models.ForeignKey(
        ThreatIntelligenceFeed,
        on_delete=models.CASCADE,
        related_name="intel_items",
        verbose_name=_("Feed Source")
    )
    item_type = models.CharField(_("Item Type"), max_length=50, choices=TYPE_CHOICES)
    value = models.TextField(_("Value"))
    first_seen = models.DateTimeField(_("First Seen"), auto_now_add=True)
    last_seen = models.DateTimeField(_("Last Seen"), auto_now=True)
    confidence = models.CharField(_("Confidence"), max_length=10, 
                                 choices=(
                                     ('low', 'Low'),
                                     ('medium', 'Medium'),
                                     ('high', 'High')
                                 ),
                                 default='medium')
    is_malicious = models.BooleanField(_("Is Malicious"), default=False)
    tlp = models.CharField(_("TLP"), max_length=10,
                          choices=(
                              ('white', 'TLP:WHITE'),
                              ('green', 'TLP:GREEN'),
                              ('amber', 'TLP:AMBER'),
                              ('red', 'TLP:RED'),
                          ),
                          default='amber')
    tags = models.TextField(_("Tags"), blank=True, help_text=_("Comma-separated list of tags"))
    description = models.TextField(_("Description"), blank=True)
    external_id = models.CharField(_("External ID"), max_length=255, blank=True,
                                 help_text=_("ID in the original source system"))
    external_url = models.URLField(_("External URL"), blank=True, 
                                 help_text=_("URL to the item in the source system"))
    
    # Campos adicionais para metadados do MISP
    creator_org = models.CharField(_("Creator Organization"), max_length=255, blank=True)
    owner_org = models.CharField(_("Owner Organization"), max_length=255, blank=True)
    creator_user = models.CharField(_("Creator User"), max_length=255, blank=True)
    event_date = models.DateTimeField(_("Event Date"), null=True, blank=True)
    attribute_count = models.IntegerField(_("Number of Attributes"), default=0)
    correlation_count = models.IntegerField(_("Number of Correlations"), default=0)
    distribution = models.CharField(_("Distribution"), max_length=50, blank=True)
    
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    
    class Meta:
        verbose_name = _("Threat Intelligence Item")
        verbose_name_plural = _("Threat Intelligence Items")
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['value']),
            models.Index(fields=['item_type']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['feed', 'item_type', 'value', 'external_id'], 
                                  name='unique_intel_item')
        ]
    
    def __str__(self):
        return f"{self.get_item_type_display()}: {self.value[:50]}"


class MISPTag(models.Model):
    """
    Modelo para armazenar tags de MISP
    """
    feed = models.ForeignKey(
        MISPInstance,
        on_delete=models.CASCADE,
        related_name="misp_tags",
        verbose_name=_("MISP Instance")
    )
    name = models.CharField(_("Tag Name"), max_length=255)
    colour = models.CharField(_("Colour"), max_length=7, blank=True)
    external_id = models.CharField(_("External ID"), max_length=255)
    is_hidden = models.BooleanField(_("Is Hidden"), default=False)
    is_system = models.BooleanField(_("Is System Tag"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("MISP Tag")
        verbose_name_plural = _("MISP Tags")
        ordering = ['name']
        unique_together = ['feed', 'external_id']

    def __str__(self):
        return self.name


class MISPGalaxy(models.Model):
    """
    Modelo para armazenar galáxias do MISP
    """
    feed = models.ForeignKey(
        MISPInstance,
        on_delete=models.CASCADE,
        related_name="misp_galaxies",
        verbose_name=_("MISP Instance")
    )
    external_id = models.CharField(_("External ID"), max_length=255)
    name = models.CharField(_("Name"), max_length=255)
    type = models.CharField(_("Type"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    version = models.CharField(_("Version"), max_length=50, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("MISP Galaxy")
        verbose_name_plural = _("MISP Galaxies")
        ordering = ['name']
        unique_together = ['feed', 'external_id']

    def __str__(self):
        return f"{self.name} ({self.type})"


class MISPCluster(models.Model):
    """
    Modelo para armazenar clusters de galáxias do MISP
    """
    galaxy = models.ForeignKey(
        MISPGalaxy,
        on_delete=models.CASCADE,
        related_name="clusters",
        verbose_name=_("MISP Galaxy")
    )
    external_id = models.CharField(_("External ID"), max_length=255)
    uuid = models.CharField(_("UUID"), max_length=255, blank=True)
    value = models.CharField(_("Value"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    source = models.CharField(_("Source"), max_length=255, blank=True)
    meta = models.JSONField(_("Metadata"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("MISP Cluster")
        verbose_name_plural = _("MISP Clusters")
        ordering = ['value']
        unique_together = ['galaxy', 'external_id']

    def __str__(self):
        return self.value 