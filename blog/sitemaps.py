from django.contrib.sitemaps import Sitemap
from .models import Post

class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Post.published.all()
        # get_absolute_url wykonuje się automatycznie
        # "location" pod priority --> jezeli chcemy ustawic adres url dla kazdego postu
    
    def lastmod(self, obj):
        return obj.updated