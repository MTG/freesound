from django.core.paginator import Paginator, InvalidPage

def paginate(request, qs, items_per_page=20, given_page=False):
    paginator = Paginator(qs, items_per_page)

    try:
        if not given_page:
            current_page = int(request.GET.get("page", 1))
        else:
            current_page = int(given_page)
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1
    
    return dict(paginator=paginator, current_page=current_page, page=page)
