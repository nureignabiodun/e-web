from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import *
from .forms import *
from django.utils import timezone
from datetime import timedelta


def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(available=True)[:8]
    latest_products = Product.objects.filter(available=True).order_by('-created_at')[:12]

    context = {
        'categories': categories,
        'featured_products': featured_products,
        'latest_products': latest_products,
    }
    return render(request, 'store/home.html', context)


def product_list(request, category_slug=None):
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Search functionality
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    # Sorting
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'products': page_obj,
        'selected_category': category_slug,
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]

    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not product.is_in_stock():
        messages.error(request, 'This product is out of stock.')
        return redirect('store:product_detail', slug=product.slug)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f'{product.name} quantity updated in cart.')
    else:
        messages.success(request, f'{product.name} added to cart.')

    return redirect('store:cart_view')


@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.get_total_price() for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'store/cart.html', context)


@login_required
def update_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                cart_item.delete()
                return redirect('store:cart_view')

        cart_item.save()

    return redirect('store:cart_view')


@login_required
def remove_from_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('store:cart_view')


@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('store:cart_view')

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        if form.is_valid():
            # Get or create address
            address_id = form.cleaned_data.get('address')
            if address_id:
                shipping_address = get_object_or_404(Address, id=address_id, user=request.user)
            else:
                # Create new address
                shipping_address = Address.objects.create(
                    user=request.user,
                    full_name=form.cleaned_data['full_name'],
                    phone_number=form.cleaned_data['phone_number'],
                    address_line1=form.cleaned_data['address_line1'],
                    address_line2=form.cleaned_data['address_line2'],
                    city=form.cleaned_data['city'],
                    state=form.cleaned_data['state'],
                    postal_code=form.cleaned_data['postal_code'],
                    country=form.cleaned_data['country'],
                )

            # Calculate total
            total = sum(item.get_total_price() for item in cart_items)

            # Create order
            order = Order.objects.create(
                user=request.user,
                status='pending',
                payment_method=form.cleaned_data['payment_method'],
                total_amount=total,
                shipping_address=shipping_address,
            )

            # Create order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                )

                # Update product stock
                item.product.stock -= item.quantity
                item.product.save()

            # Clear cart
            cart_items.delete()

            # Create initial tracking
            OrderTracking.objects.create(
                order=order,
                status='pending',
                description='Order has been placed',
                updated_by=request.user,
            )

            # Create payment record
            Payment.objects.create(
                order=order,
                amount=total,
                payment_method=form.cleaned_data['payment_method'],
            )

            messages.success(request, f'Order placed successfully! Order Number: {order.order_number}')
            return redirect('store:order_detail', order_id=order.id)

    else:
        initial_data = {}
        if default_address:
            initial_data = {
                'full_name': default_address.full_name,
                'phone_number': default_address.phone_number,
                'address_line1': default_address.address_line1,
                'address_line2': default_address.address_line2,
                'city': default_address.city,
                'state': default_address.state,
                'postal_code': default_address.postal_code,
                'country': default_address.country,
            }

        form = CheckoutForm(initial=initial_data)

    total = sum(item.get_total_price() for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total': total,
        'form': form,
        'addresses': addresses,
        'default_address': default_address,
    }
    return render(request, 'store/checkout.html', context)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'store/order_list.html', context)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    tracking_history = order.tracking.all()

    context = {
        'order': order,
        'tracking_history': tracking_history,
    }
    return render(request, 'store/order_detail.html', context)


def register(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            # FIX: Let UserCreationForm handle password setting automatically
            user = form.save()  # This automatically sets the password correctly

            # Create user profile
            UserProfile.objects.create(user=user)

            messages.success(request, 'Account created successfully! Please login.')
            return redirect('store:login')
    else:
        form = UserRegistrationForm()

    return render(request, 'store/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, 'Welcome back!')
                return redirect('store:home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'store/login.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('store:home')


@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('store:profile')
    else:
        profile_form = UserProfileForm(instance=user_profile)

    context = {
        'profile_form': profile_form,
        'addresses': addresses,
    }
    return render(request, 'store/profile.html', context)


@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)

        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            # If this is the first address, make it default
            if not Address.objects.filter(user=request.user).exists():
                address.is_default = True
            else:
                address.is_default = form.cleaned_data.get('is_default', False)

            address.save()

            # If this is set as default, unset others
            if address.is_default:
                Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)

            messages.success(request, 'Address added successfully.')
            return redirect('store:profile')
    else:
        form = AddressForm()

    return render(request, 'store/add_address.html', {'form': form})


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)

        if form.is_valid():
            address = form.save(commit=False)

            if form.cleaned_data.get('is_default'):
                Address.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True

            address.save()

            messages.success(request, 'Address updated successfully.')
            return redirect('store:profile')
    else:
        form = AddressForm(instance=address)

    return render(request, 'store/edit_address.html', {'form': form, 'address': address})


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, 'Address deleted successfully.')
    return redirect('store:profile')


@login_required
def set_default_address(request, address_id):
    Address.objects.filter(user=request.user).update(is_default=False)
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, 'Default address updated.')
    return redirect('store:profile')


# Admin Views
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    total_revenue = Order.objects.filter(payment_status=True).aggregate(
        total=models.Sum('total_amount')
    )['total'] or 0

    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    products = Product.objects.all().order_by('-created_at')[:20]
    categories = Category.objects.all()

    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/admin_dashboard.html', context)


@login_required
def admin_order_list(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    status_filter = request.GET.get('status')
    if status_filter:
        orders = Order.objects.filter(status=status_filter).order_by('-created_at')
    else:
        orders = Order.objects.all().order_by('-created_at')

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'store/admin_order_list.html', context)


@login_required
def admin_order_detail(request, order_id):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    order = get_object_or_404(Order, id=order_id)
    tracking_history = order.tracking.all()

    if request.method == 'POST':
        form = OrderStatusForm(request.POST)

        if form.is_valid():
            new_status = form.cleaned_data['status']
            description = form.cleaned_data['description']
            location = form.cleaned_data['location']

            # Update order status
            order.status = new_status
            order.save()

            # Create tracking update
            OrderTracking.objects.create(
                order=order,
                status=new_status,
                description=description,
                location=location,
                updated_by=request.user,
            )

            messages.success(request, 'Order status updated successfully.')
            return redirect('store:admin_order_detail', order_id=order.id)
    else:
        form = OrderStatusForm(initial={'status': order.status})

    context = {
        'order': order,
        'tracking_history': tracking_history,
        'form': form,
    }
    return render(request, 'store/admin_order_detail.html', context)


@login_required
def admin_product_list(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    products = Product.objects.all().order_by('-created_at')
    context = {'products': products}
    return render(request, 'store/admin_product_list.html', context)


@login_required
def admin_product_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully.')
            return redirect('store:admin_product_list')
    else:
        form = ProductForm()

    return render(request, 'store/admin_product_form.html', {'form': form})


@login_required
def admin_product_edit(request, product_id):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('store:admin_product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'store/admin_product_form.html', {'form': form, 'product': product})


@login_required
def admin_product_delete(request, product_id):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('store:admin_product_list')


# Context Processor
def cart_items_count(request):
    count = 0
    if request.user.is_authenticated:
        count = Cart.objects.filter(user=request.user).count()
    return {'cart_items_count': count}


@login_required
def admin_category_list(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    categories = Category.objects.all().order_by('name')
    context = {'categories': categories}
    return render(request, 'store/admin_category_list.html', context)


@login_required
def admin_category_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('store:home')

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully.')
            return redirect('store:admin_dashboard')
    else:
        form = CategoryForm()

    return render(request, 'store/admin_category_form.html', {'form': form})