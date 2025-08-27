from django.shortcuts import render, redirect
# 1. Değişiklik: "models" importu düzeltildi
from .models import Item, Bid
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from datetime import datetime
from emg.settings import BASE_URL

# Create your views here.
from django.http import HttpResponse


def index(request):
    category = request.GET.get('category', 'all')
    sort = request.GET.get('sort', 'active')
    
    if category == 'all':
        item_list = Item.objects.all()
    else:
        item_list = Item.objects.filter(category=category)

    item_list = list(item_list) 

    if sort=='cheapest':
        item_list.sort(key=(lambda item: item.get_current_bid()))
    elif sort=='priciest':
        item_list.sort(key=(lambda item: -item.get_current_bid()))
    elif sort=='newest':
        item_list.sort(key=(lambda item: item.created_at), reverse=True)
    elif sort=='active':
        item_list.sort(key=(lambda item: item.last_bid_at()), reverse=True)

    context = {
        'BASE_URL': BASE_URL,
        'category': category,
        'sort': sort,
        'item_list': item_list
    }
    return render(request, 'main/index.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Kayıt olma (signup) mantığı
        if 'confirm_password' in request.POST:
            confirm_password = request.POST.get('confirm_password')
            if not username or not password or password != confirm_password:
                # 2. Değişiklik: render_to_response yerine render kullanıldı
                return render(request, 'main/login.html', {'BASE_URL': BASE_URL, 'signup_error': True})
            try:
                User.objects.create_user(username, password=password)
            except IntegrityError:
                return render(request, 'main/login.html', {'BASE_URL': BASE_URL, 'already_exists_error': True})
        
        # Giriş yapma (login) mantığı
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # 3. Değişiklik: is_authenticated() parantezleri kaldırıldı
            if request.user.is_authenticated:
                return redirect(BASE_URL + "me")
        
        # Giriş başarısızsa
        return render(request, 'main/login.html', {'BASE_URL': BASE_URL, 'login_error': True})
    
    # GET isteği ise boş login sayfasını göster
    return render(request, 'main/login.html', {'BASE_URL': BASE_URL})

def logout_view(request):
    logout(request)
    return redirect(BASE_URL + "me")

def me(request):
    # 3. Değişiklik: is_authenticated() parantezleri kaldırıldı
    if request.user.is_authenticated:
        # Orijinal koddaki gibi verimsiz sorgu korunmuştur.
        # Daha verimli bir yol: winning_items = Item.objects.filter(winner=request.user)
        all_items = Item.objects.all()
        winning_items = []
        beaten_items = []
        for item in all_items:
            # Sadece kullanıcının teklif verdiği item'ları kontrol et
            if Bid.objects.filter(user=request.user, item=item).exists():
                if item.get_winner() == request.user:
                    winning_items.append(item)
                else:
                    beaten_items.append(item)
        
        return render(request, 'main/me.html', {
            'BASE_URL': BASE_URL,
            'winning_items': winning_items,
            'beaten_items': beaten_items
        })
    else:
        return redirect(BASE_URL)

def item(request, id):
    item = Item.objects.get(id=id)
    current_price = item.get_current_bid()
    time_left = item.get_time_left()

    bids_for_item = []
    if request.user.is_superuser:
        bids_for_item = Bid.objects.filter(item=item).order_by('-price', 'created_at')

    if request.method == 'POST':
        if not time_left:
            return redirect(BASE_URL)

        bid_price = request.POST.get('bid_price')
        try:
            bid_price = float(bid_price)
        except (ValueError, TypeError):
            return render(request, 'main/item.html', {'BASE_URL': BASE_URL, 'item': item, 'current_price': current_price, 'bid_error': True})
        
        if (bid_price <= current_price or not (bid_price * 4).is_integer()):
            return render(request, 'main/item.html', {'BASE_URL': BASE_URL, 'item': item, 'current_price': current_price, 'bid_error': True})
        
        # 3. Değişiklik: is_authenticated() parantezleri kaldırıldı
        if not request.user.is_authenticated:
            return redirect(BASE_URL)

        my_bid, created = Bid.objects.update_or_create(
            user=request.user, item=item,
            defaults={'price': bid_price, 'created_at': datetime.now()}
        )
        
        current_price = item.get_current_bid()

        return render(request, 'main/item.html', {
            'BASE_URL': BASE_URL,    
            'item': item,
            'bids_for_item': bids_for_item,
            'current_price': current_price,
            'bid_success': True,
            'beaten': my_bid.price if item.get_winner() != request.user else False
        })
    else:
        beaten = False
        # 3. Değişiklik: is_authenticated() parantezleri kaldırıldı
        if request.user.is_authenticated:
            try:
                my_bid = Bid.objects.get(user=request.user, item=item)
                beaten = my_bid.price
            except Bid.DoesNotExist:
                pass

        winner = None
        if not time_left:
            winner = item.get_winner()

        return render(request, 'main/item.html', {
            'BASE_URL': BASE_URL,    
            'item': item,
            'bids_for_item': bids_for_item,
            'current_price': current_price,
            'beaten': beaten if item.get_winner() != request.user else False,
            'winner': winner
        })
