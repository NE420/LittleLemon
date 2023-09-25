from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
# Create your models here.

class Category(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField()
    

class menuItem(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    price = models.DecimalField(max_digits=6, decimal_places= 2, db_index=True)
    featured = models.BooleanField(db_index=True, default=False)
    category = models.ForeignKey(Category, on_delete = models.PROTECT)


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete= models.CASCADE)
    menuitem = models.ForeignKey(menuItem, on_delete= models.CASCADE)
    quantity = models.SmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places= 2)
    price = models.DecimalField(max_digits=6, decimal_places= 2)
    class Meta:
        unique_together = ('menuitem', 'user')

class Order(models.Model):
    user = models.ForeignKey(User, on_delete= models.CASCADE)
    delivery_crew = models.ForeignKey(User, on_delete= models.SET_NULL, related_name="delivery_crew", null=True)
    status = models.BooleanField(db_index=True, default=0)
    total = models.DecimalField(max_digits=6, decimal_places= 2)
    date = models.DateField(db_index=True)
    
class OrderItem(models.Model):
    order = models.ForeignKey(User, on_delete= models.CASCADE)
    menuitem = models.ForeignKey(menuItem, on_delete= models.CASCADE)
    quantity = models.SmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places= 2)
    price = models.DecimalField(max_digits=6, decimal_places= 2)
    class Meta:
        unique_together = ('order', 'menuitem')
        
def today():
    return timezone.now().date()