import stripe
import os

# DO NOT hardcode your keys! Use .env file
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Anchor Cloud Pro Tier'},
                    'unit_amount': 999, # $9.99
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:5000/success.html', # Redirect after payment
            cancel_url='http://localhost:5000/index.html',
        )
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 403