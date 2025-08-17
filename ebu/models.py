from django.db import models
from django.contrib.gis.db import models

class Province(models.Model):
  
    pCode = models.CharField(max_length=15)  
    admNameEng = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.admNameEng} ({self.pCode})"
    
    class Meta: 
        db_table = 'province'
        
class Kabupaten(models.Model):
  
    kCode = models.CharField(max_length=15)  
    admNameEng = models.CharField(max_length=100)
    province= models.ForeignKey(Province,on_delete=models.CASCADE,blank=True)
    
    def __str__(self):
        return f"{self.admNameEng} ({self.kCode})"
    
    class Meta: 
        db_table = 'kabupaten'


class User(models.Model):
    admcode = models.CharField(max_length=20, blank=False, null=False) 
    lgName = models.CharField(max_length=100)
    emailId = models.CharField(max_length=100, blank=True)
    phoneNumber = models.CharField(max_length=15)  # Changed from IntegerField
    dbCloudLink = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.lgName} ({self.admcode})"
    
    class Meta: 
        
        db_table = 'user'


class Link(models.Model):
    id = models.AutoField(primary_key=True)  
    admCode = models.CharField( null=True, blank=True, db_column='admCode')
    linkNo = models.CharField(null=True, max_length=100, db_column='linkNo')
    linkCode = models.CharField( null=False, max_length=100, db_column='linkCode')
    linkName = models.CharField(max_length=250, null=False, blank=False, db_column='linkName')
    linkLengthOfficial = models.FloatField(null=False, blank=False, db_column='linkLengthOfficial')
    linkLengthActual = models.FloatField(null=False, blank=False, db_column='linkLengthActual')

    status = models.CharField(max_length=10, null=True, blank=True, db_column='status')
    function = models.CharField(max_length=10, null=True, blank=True, db_column='function')
    class_field = models.CharField(max_length=10, null=True, blank=True, db_column='class')

    wti = models.IntegerField(null=True, blank=True, db_column='wti')
    mca2 = models.IntegerField(null=True, blank=True, db_column='mca2')
    mca3 = models.IntegerField(null=True, blank=True, db_column='mca3')
    mca4 = models.IntegerField(null=True, blank=True, db_column='mca4')
    mca5 = models.IntegerField(null=True, blank=True, db_column='mca5')

    projectNumber = models.CharField(null=True, blank=True, max_length=100, db_column='projectNumber')
    cumesa = models.FloatField(null=True, blank=True, db_column='cumesa')
    esa0 = models.FloatField(null=True, blank=True, db_column='esa0')
    aadt = models.IntegerField(null=True, blank=True, db_column='aadt')
    accessStatus = models.CharField(null=True, blank=True, max_length=100, db_column='accessStatus')

    def __str__(self):
        return f"{self.linkName} ({self.linkNo}) - ({self.linkCode})"
    
    class Meta:
        db_table = 'link'



class Alignment(models.Model):
    admCode = models.CharField(max_length=50)
    linkNo = models.ForeignKey(Link, on_delete=models.CASCADE, related_name='alignments')
    linkGeometry = models.GeometryField(srid=4326)  # You can also use LineStringField if always lines

    def __str__(self):
        return f"Alignment for {self.linkNo.linkName} ({self.admCode})"
    
    class Meta:
        db_table = 'alignment'
        
    
class DBfile(models.Model):
    admCode = models.CharField(max_length=50)
    fileUrl = models.URLField(max_length=500)

    def __str__(self):
        return f"DB File for AdmCode {self.admCode} → {self.fileUrl}"

    class Meta:
        db_table = 'dbfile'

class DrpFile(models.Model):
    admCode = models.CharField(max_length=50)
    drpFile = models.FileField(upload_to="drp_files/")   # saves file in MEDIA_ROOT/drp_files/

    def __str__(self):
        return f"DRP File for AdmCode {self.admCode}: {self.drpFile.name}"

    class Meta:
        db_table = 'drpfile'
