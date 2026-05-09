# from django.db import models

# Create your models here.
from django.db import models


class Operator(models.Model):
    reference = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.name} ({self.reference})"


class Country(models.Model):
    reference = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.name} ({self.reference})"


class Location(models.Model):
    reference = models.CharField(max_length=64, unique=True)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    postal_code = models.CharField(max_length=32, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.reference


class EVSE(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="evses")
    physical_identifier = models.CharField(max_length=128)
    status = models.CharField(max_length=32)

    def __str__(self) -> str:
        return self.physical_identifier


class Connector(models.Model):
    evse = models.ForeignKey(EVSE, on_delete=models.CASCADE, related_name="connectors")
    power = models.IntegerField()
    standard = models.CharField(max_length=64)

    def __str__(self) -> str:
        return f"{self.standard} {self.power}kW"