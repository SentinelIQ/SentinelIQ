from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Tag(models.Model):
    """Tag model for categorizing alerts and cases"""
    
    # Color choices for tags
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    SUCCESS = 'success'
    DANGER = 'danger'
    WARNING = 'warning'
    INFO = 'info'
    LIGHT = 'light'
    DARK = 'dark'
    
    COLOR_CHOICES = [
        (PRIMARY, _('Blue')),
        (SECONDARY, _('Gray')),
        (SUCCESS, _('Green')),
        (DANGER, _('Red')),
        (WARNING, _('Yellow')),
        (INFO, _('Light Blue')),
        (LIGHT, _('White')),
        (DARK, _('Black')),
    ]
    
    name = models.CharField(_('Name'), max_length=50)
    color = models.CharField(
        _('Color'),
        max_length=20,
        choices=COLOR_CHOICES,
        default=PRIMARY,
    )
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']


class Observable(models.Model):
    """Model for observables or indicators of compromise (IOCs)"""
    
    # Observable types
    IP = 'ip'
    DOMAIN = 'domain'
    URL = 'url'
    EMAIL = 'email'
    HASH_MD5 = 'hash_md5'
    HASH_SHA1 = 'hash_sha1'
    HASH_SHA256 = 'hash_sha256'
    FILENAME = 'filename'
    FILEPATH = 'filepath'
    REGISTRY = 'registry'
    USER_AGENT = 'user_agent'
    PROCESS = 'process'
    CVE = 'cve'
    OTHER = 'other'
    
    TYPE_CHOICES = [
        (IP, _('IP Address')),
        (DOMAIN, _('Domain')),
        (URL, _('URL')),
        (EMAIL, _('Email')),
        (HASH_MD5, _('MD5 Hash')),
        (HASH_SHA1, _('SHA1 Hash')),
        (HASH_SHA256, _('SHA256 Hash')),
        (FILENAME, _('Filename')),
        (FILEPATH, _('Filepath')),
        (REGISTRY, _('Registry')),
        (USER_AGENT, _('User Agent')),
        (PROCESS, _('Process')),
        (CVE, _('CVE')),
        (OTHER, _('Other')),
    ]
    
    # Confidence levels
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    
    CONFIDENCE_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
    ]
    
    # PAP (Permissible Actions Protocol) levels
    PAP_UNKNOWN = 'unknown'
    PAP_WHITE = 'white'
    PAP_GREEN = 'green'
    PAP_AMBER = 'amber'
    PAP_RED = 'red'
    
    PAP_CHOICES = [
        (PAP_UNKNOWN, _('Unknown (PAP:UNKNOWN)')),
        (PAP_WHITE, _('White (PAP:WHITE)')),
        (PAP_GREEN, _('Green (PAP:GREEN)')),
        (PAP_AMBER, _('Amber (PAP:AMBER)')),
        (PAP_RED, _('Red (PAP:RED)')),
    ]
    
    value = models.CharField(_('Value'), max_length=255)
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    confidence = models.CharField(
        _('Confidence'), 
        max_length=10,
        choices=CONFIDENCE_CHOICES,
        default=MEDIUM
    )
    is_malicious = models.BooleanField(_('Malicious'), default=False)
    pap = models.CharField(
        _('PAP Level'),
        max_length=10,
        choices=PAP_CHOICES,
        default=PAP_UNKNOWN,
        help_text=_('Permissible Actions Protocol: Defines how this observable can be shared or used.')
    )
    description = models.TextField(_('Description'), blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    last_seen = models.DateTimeField(_('Last Seen'), null=True, blank=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='observables',
    )
    
    # Relationships to Alert and Case models will be defined on those models
    # using ManyToManyField
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.value}"
    
    class Meta:
        verbose_name = _('Observable')
        verbose_name_plural = _('Observables')
        ordering = ['-updated_at']


class MitreTactic(models.Model):
    """MITRE ATT&CK Tactics (TA)"""
    tactic_id = models.CharField(_('Tactic ID'), max_length=50, unique=True)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    url = models.URLField(_('URL'), blank=True)
    
    def __str__(self):
        return f"{self.tactic_id}: {self.name}"
    
    class Meta:
        verbose_name = _('MITRE Tactic')
        verbose_name_plural = _('MITRE Tactics')
        ordering = ['tactic_id']


class MitreTechnique(models.Model):
    """MITRE ATT&CK Techniques (T)"""
    technique_id = models.CharField(_('Technique ID'), max_length=50, unique=True)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    url = models.URLField(_('URL'), blank=True)
    tactics = models.ManyToManyField(MitreTactic, related_name='techniques')
    
    def __str__(self):
        return f"{self.technique_id}: {self.name}"
    
    class Meta:
        verbose_name = _('MITRE Technique')
        verbose_name_plural = _('MITRE Techniques')
        ordering = ['technique_id']


class MitreSubTechnique(models.Model):
    """MITRE ATT&CK Sub-techniques (T.XXX)"""
    sub_technique_id = models.CharField(_('Sub-technique ID'), max_length=50, unique=True)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    url = models.URLField(_('URL'), blank=True)
    parent_technique = models.ForeignKey(
        MitreTechnique,
        on_delete=models.CASCADE,
        related_name='subtechniques'
    )
    
    def __str__(self):
        return f"{self.sub_technique_id}: {self.name}"
    
    class Meta:
        verbose_name = _('MITRE Sub-technique')
        verbose_name_plural = _('MITRE Sub-techniques')
        ordering = ['sub_technique_id']


class MitreAttackGroup(models.Model):
    """
    Modelo para agrupar elementos MITRE ATT&CK relacionados (táticas, técnicas, subtécnicas)
    que podem ser associados a casos e alertas como parte de uma cadeia de ataque completa.
    """
    name = models.CharField(_('Nome'), max_length=255)
    description = models.TextField(_('Descrição'), blank=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='mitre_attack_groups',
        verbose_name=_('Organização')
    )
    
    # Relações com elementos MITRE
    tactics = models.ManyToManyField(
        MitreTactic, 
        verbose_name=_('Táticas'),
        related_name='attack_groups',
        blank=True
    )
    techniques = models.ManyToManyField(
        MitreTechnique, 
        verbose_name=_('Técnicas'),
        related_name='attack_groups',
        blank=True
    )
    subtechniques = models.ManyToManyField(
        MitreSubTechnique, 
        verbose_name=_('Sub-técnicas'),
        related_name='attack_groups',
        blank=True
    )
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Grupo MITRE ATT&CK')
        verbose_name_plural = _('Grupos MITRE ATT&CK')
        ordering = ['-updated_at']
