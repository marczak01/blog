from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery, TrigramSimilarity
from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponse
from blog.models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import EmailPostForm, CommentForm, SearchForm
from django.views.generic import ListView
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
# Create your views here.
#    test

# class PostListView(ListView):
#     """
#     Alternatywny widok listy postów (zamiast funkcji ponizej)
#     Uycie klasy zamiast funkcji w celu obslugi wyświetlenia
#     postow na stronie.
#     """
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'

def post_list(request, tag_slug=None):
    """
    Widok listy postów. Z uzyciem funkcji zamiast klasy.
    Przy klasach potrzebuje sporo nauki..
    """
    post_list = Post.published.all()
    templatefilename = 'blog/post/list.html'
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug) 
        #tworzy jednoobiektową liste, ktora ma tylko wybrany przez nas tag
        post_list = post_list.filter(tags__in=[tag]) 
        #nadpisuje liste post_list nową listą ktora zawiera
        #wszystkie posty zawierające wybrany tag

    #stronicowanie z 3 elementami na stronę
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except EmptyPage:
        # jezeli zmienna page_number jest poza zakresem wyslij ostatnia strone wynikow
        posts = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        # jezeli zmienna page_number nie jest liczbą zwróć pierwszą strone wynikow
        posts = paginator.page(1)

    context = {
        'posts': posts,
        'tag': tag
    }
    return render(request, templatefilename, context)


# def post_detail(request, id):
#     templatefilename = 'blog/post/detail.html'
#     try:
#         post = Post.published.get(id=id)
#     except Post.DoesNotExist:
#         raise Http404("Nie znaleziono posta.")

#     context = { 'post': post }
#     return render(request, templatefilename, context)

# ponizej wersja ze skrótem get_object_or_404 zamiast try:except:
def post_detail(request, year, month, day, post):
    templatefilename = 'blog/post/detail.html'
    post = get_object_or_404(Post,
                             slug = post,
                             publish__year = year,
                             publish__month = month,
                             publish__day = day,
                             status=Post.Status.PUBLISHED)
    
    # lista aktywnych komentarzy do tego posta
    comments_list = post.comments.filter(active=True)
    # formularz do wprowadzania komentarzy uzytkownika
    form = CommentForm()
    post_tags = post.tags.all()
    # lista podobnych postow
    # lista wszystkich tagow dodanych do posta
    # values_list() zwraca listę krotek [(1,), (2,), (3,), ...] 
    # uzywajac flat=True otrzymamy liste jednorodna [1, 2, 3, ...]
    post_tags_ids = post.tags.values_list('id', flat=True) 
    # lista wszystkich postów, które mają takie same tagi co z listy powyzej
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    # dodatkow
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    paginator = Paginator(comments_list, 4)
    page_number = request.GET.get('page', 1)
    try:
        comments = paginator.page(page_number)
    except EmptyPage:
        # jezeli zmienna page_number jest poza zakresem wyslij ostatnia strone wynikow
        comments = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        # jezeli zmienna page_number nie jest liczbą zwróć pierwszą strone wynikow
        comments = paginator.page(1)

    context = { 'post': post,
                'comments': comments,
                'comments_list': comments_list,
                'form': form,
                'similar_posts': similar_posts,
                'post_tags': post_tags }
    return render(request, templatefilename, context)


def post_share(request, post_id):
    # pobierz post wedlug id
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':
        # formularz zostal przeslany
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # pomyslnie zweryfikowano poprawnosc pól formularza
            cd = form.cleaned_data
            # wyślij email
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} poleca Ci przeczytanie {post.title}"
            message = f"Przeczytaj {post.title} pod adresem {post_url}\n\nKomentarz {cd['name']}: \n\n{cd['comments']}"
            send_mail(subject, message, cd['email'], [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
        # return form.errors

    context = {
        'post': post,
        'form': form,
        'sent': sent
    }
    return render(request, 'blog/post/share.html', context)


@require_POST
def post_comment(request, post_id):
    niedozwolone = ['chuj', 'szmata', 'bitch']
    post = get_object_or_404(Post,
                             id=post_id,
                             status=Post.Status.PUBLISHED)
    comment = None
    # opublikowano komentarz
    form = CommentForm(data=request.POST)
    if form.is_valid():
        for x in niedozwolone:
            if x in form.cleaned_data['body'].lower():
                comment = form.save(commit=False)
                comment.active = False
                comment.post = post
                comment.save()
                return HttpResponse('Uzyłeś niedozwolonego slowa. Nie mozemy opublikowac twojego komentarza!')
        else:
            # utwórz obiekt Comment bez zapisywania go w bazie danych
            comment = form.save(commit=False)
            # przypisz komentarz do posta
            comment.post = post
            # zapisz komentarz w bazie danych
            comment.save()

    context = {
        'form': form,
        'comment': comment,
        'post': post
    }

    return render(request, 'blog/post/comment.html', context)


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', weight='A') + SearchVector('body', weight='B')
            search_query = SearchQuery(query, config='english')
            results = Post.published.annotate(similarity=TrigramSimilarity('title', query), ).filter(similarity__gt=0.1).order_by('-similarity')

    context = {
        'form': form,
        'query': query,
        'results': results
    }

    return render(request, 'blog/post/search.html', context)