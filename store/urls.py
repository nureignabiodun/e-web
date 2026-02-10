# store/urls.py
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Public views
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Cart views
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:cart_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Checkout and orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Profile and addresses
    path('profile/', views.profile, name='profile'),
    path('profile/address/add/', views.add_address, name='add_address'),
    path('profile/address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('profile/address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('profile/address/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),

    # Admin views - CHANGED URL PATTERN
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  # Changed from admin/dashboard/
    path('dashboard/orders/', views.admin_order_list, name='admin_order_list'),
    path('dashboard/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('dashboard/products/', views.admin_product_list, name='admin_product_list'),
    path('dashboard/products/create/', views.admin_product_create, name='admin_product_create'),
    path('dashboard/products/edit/<int:product_id>/', views.admin_product_edit, name='admin_product_edit'),
    path('dashboard/products/delete/<int:product_id>/', views.admin_product_delete, name='admin_product_delete'),

    path('dashboard/categories/', views.admin_category_list, name='admin_category_list'),
    path('dashboard/categories/create/', views.admin_category_create, name='admin_category_create'),
]