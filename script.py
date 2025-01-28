import requests
import csv
import sys
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os
import json
import argparse

# Load environment variables from .env file
load_dotenv()

WSOL_PLACEHOLDER = 'So11111111111111111111111111111111111111112'
PUMPFUN_WALLET = '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'

# Helius API configuration
API_KEY = os.getenv('HELIUS_API_KEY')
BASE_URL = f"https://api.helius.xyz/v0/addresses"

# Constants
EST = pytz.timezone('America/New_York')

def fetch_enriched_transactions(wallet_address, limit=50):
    transactions = []
    before_signature = None
    url = f"{BASE_URL}/{wallet_address}/transactions?api-key={API_KEY}"

    while True:
        payload = {
            "limit": limit
        }
        if before_signature:
            payload["before"] = before_signature

        response = requests.get(url, params=payload)

        if response.status_code == 200:
            data = response.json()

            if data:
                transactions.extend(data)
                
                # If less than the limit is returned, there are no more transactions
                if len(data) < limit:
                    break
                
                # Get the last transaction's signature and continue pagination
                before_signature = data[-1]['signature']
            else:
                print("No more transactions found for this wallet.")
                break
        else:
            print(f"Failed to fetch enriched transactions. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            break

    return transactions
    
def is_swap(transaction):
    return 'type' in transaction and transaction['type'] == 'SWAP'
    
def is_transfer(transaction):
    return 'type' in transaction and (transaction['type'] == 'TRANSFER' or transaction['type'] == 'UNKNOWN')
    
def is_swap_or_transfer(transaction):
    return is_swap(transaction) or is_transfer(transaction)

def process_transactions(transactions, wallet_address, token_address, debug=False):
    if not transactions:
        print("No transactions to process.")
        return [], 0, 0, 0, 0, 0, set(), None, None, 0

    total_tokens_bought = 0
    total_tokens_sold = 0
    total_tokens_received = 0
    total_tokens_sent = 0
    max_tokens_held = 0
    current_tokens_held = 0
    total_sol_spent = 0
    total_sol_received = 0
    total_sol_fees = 0
    first_purchase_date = None
    last_sale_date = None
    connected_wallets = set()

    processed_data = []

    for i, transaction in enumerate(transactions):
        signature = transaction['signature']
        timestamp = datetime.fromtimestamp(transaction['timestamp'], tz=EST).strftime('%Y-%m-%d %H:%M:%S')
        sol_value = 0
        sol_fees = 0
        token_amount = 0
        is_pumpfun_transaction = False
        is_complete_transaction = False
        found_transaction_sol = False
        found_transaction_token = False
        connected_wallet = ""
        from_user_account = ""
        to_user_account = ""

        try:
            # Handle Compressed NFT Mints
            if 'type' in transaction and transaction['type'] == 'COMPRESSED_NFT_MINT':
                continue

            # Process token transfers
            if 'tokenTransfers' in transaction and transaction['tokenTransfers'] and is_swap_or_transfer(transaction):
                for transfer in transaction['tokenTransfers']:                                        
                    if 'tokenAmount' in transfer:   
                        from_user_account = transfer['fromUserAccount']
                        to_user_account = transfer['toUserAccount']
                        if transfer['toUserAccount'] == wallet_address:
                            is_valid = False
                            # Token was received (or bought)
                            if transfer['mint'] == token_address:
                                token_amount += float(transfer['tokenAmount'])
                                is_valid = True
                                found_transaction_token = True
                            elif transfer['mint'] == WSOL_PLACEHOLDER:
                                sol_value += float(transfer['tokenAmount'])
                                is_valid = True
                                found_transaction_sol = True
                            if is_valid:
                                if is_transfer(transaction):
                                    connected_wallet = transfer['fromUserAccount']
                        elif transfer['fromUserAccount'] == wallet_address:
                            is_valid = False
                            # Token was sent (or sold)
                            if transfer['mint'] == token_address:
                                token_amount -= float(transfer['tokenAmount'])
                                is_valid = True
                                found_transaction_token = True
                            elif transfer['mint'] == WSOL_PLACEHOLDER:
                                sol_value -= float(transfer['tokenAmount'])
                                is_valid = True
                                found_transaction_sol = True
                            if is_valid:                                
                                if is_transfer(transaction):
                                    connected_wallet = transfer['toUserAccount']
                    else:
                        print(f"Skipping transfer in transaction {signature} due to missing 'tokenAmount' field.")
                        
            # is this a pumpfun transaction?
            if not found_transaction_sol and found_transaction_token and 'accountData' in transaction and transaction['accountData']:                  
                for account in transaction['accountData']:
                    if account['account'] == PUMPFUN_WALLET:
                        is_pumpfun_transaction = True
                        found_transaction_sol = True
                        connected_wallet = 'pump.fun'
                        break
            
            if is_swap(transaction):
                is_complete_transaction = found_transaction_sol and found_transaction_token
            elif is_transfer(transaction):
                is_complete_transaction = found_transaction_token
                             
            # Handle transactions without token transfers (only SOL transfers)
            if is_complete_transaction and 'nativeTransfers' in transaction and transaction['nativeTransfers']:       
                if is_pumpfun_transaction:
                    for native_transfer in transaction['nativeTransfers']:
                        # pumpfun buy
                        if token_amount > 0 and native_transfer['toUserAccount'] == from_user_account and native_transfer['fromUserAccount'] == to_user_account:
                            sol_value = float(native_transfer['amount']) / 10**9  # Convert lamports to SOL (1 SOL = 10^9 lamports)
                            break    
                        #pumpfun sell
                        if token_amount < 0 and native_transfer['fromUserAccount'] == from_user_account:
                            if 'accountData' in transaction and transaction['accountData']:
                                for account in transaction['accountData']:
                                    if account['account'] == to_user_account:
                                        sol_value = abs(float(account['nativeBalanceChange']) / 10**9)  # Convert lamports to SOL
                                        break
                            break                    
                else:
                    for native_transfer in transaction['nativeTransfers']:                    
                        if native_transfer['toUserAccount'] == to_user_account:
                            # SOL was received
                            sol_fees += float(native_transfer['amount']) / 1e9
                        elif native_transfer['fromUserAccount'] == from_user_account:
                            # SOL was sent
                            sol_fees -= float(native_transfer['amount']) / 1e9
                        
            if is_complete_transaction:                                
                if token_amount > 0:
                    if first_purchase_date is None:
                        first_purchase_date = timestamp
                    total_tokens_bought += token_amount
                elif token_amount < 0:
                    last_sale_date = timestamp
                    total_tokens_sold += -token_amount
                if sol_value > 0:
                    total_sol_received += sol_value
                elif sol_value < 0:
                    total_sol_spent += -sol_value
                    
                    
                total_sol_fees += sol_fees

                if connected_wallet and connected_wallet not in connected_wallets:
                    connected_wallets.add(connected_wallet)

                # Record for CSV
                if sol_value != 0 or token_amount != 0:
                    processed_data.append({
                        'signature': signature,
                        'date_time_est': timestamp,
                        'wallet_address': connected_wallet,
                        'sol_value': sol_value,
                        'token_amount': token_amount,
                    })

                if debug:
                    print("\n#####################################")
                    print("############# JSON INFO #############")
                    print("#####################################")
                    print(json.dumps(transaction, indent=4))
                    print("\n#####################################")
                    print("############# DEBUG INFO ############")
                    print("#####################################")
                    print(f"Transaction Signature: {signature}")
                    print(f"Date: {timestamp}")
                    print(f"SOL Transferred: {sol_value}")
                    print(f"TOKENS Transferred: {token_amount}")
                    print(f"SOL Fees: {sol_fees}")
                    if is_swap(transaction):
                        if token_amount > 0:
                            print("Transaction Type: Buy")
                        elif token_amount < 0:
                            print("Transaction Type: Sell")
                    elif is_transfer(transaction):
                        if token_amount > 0:
                            print("Transaction Type: Transfer In")
                        elif token_amount < 0:
                            print("Transaction Type: Transfer Out")
                    print("#####################################")
                    print("############# TOTAL INFO ############")
                    print("#####################################")
                    print(f"Total Tokens Bought: {total_tokens_bought}")
                    print(f"Total Tokens Sold: {total_tokens_sold}")
                    print(f"Total Tokens Traded (Bought + Sold): {total_tokens_bought + total_tokens_sold}")
                    print(f"Net Total Profit/Loss in SOL: {total_sol_received - total_sol_spent}")
                    print(f"Total SOL Spent: {total_sol_spent}")
                    print(f"Total SOL Received: {total_sol_received}")
                    print(f"Connected Wallets: {', '.join(connected_wallets)}")
                    print(f"Date of First Purchase (EST): {first_purchase_date}")
                    print(f"Date of Last Sale (EST): {last_sale_date}")
                    input("Press any key to continue...")

        except Exception as e:
            print(f"Error processing transaction {signature}: {e}")
            print(json.dumps(transaction, indent=2))

        if not is_complete_transaction and debug:
            print(f"Failed to process transaction {signature}:")            
            print(json.dumps(transaction, indent=2))

    return processed_data, total_tokens_bought, total_tokens_sold, total_sol_spent, total_sol_received, connected_wallets, first_purchase_date, last_sale_date

def save_to_csv(processed_data, filename='transactions.csv', reverse=True):
    if not processed_data:
        print("No data to save to CSV.")
        return

    # Dynamically determine all the fieldnames
    all_fieldnames = set()
    for row in processed_data:
        all_fieldnames.update(row.keys())

    all_fieldnames = sorted(list(all_fieldnames))  # Sorting for consistency

    # Reverse the data if reverse is True
    if reverse:
        processed_data = processed_data[::-1]

    # Write the CSV
    with open(filename, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=all_fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(processed_data)

    print(f"Data saved to {filename}.")

def main():
    parser = argparse.ArgumentParser(description="Process enriched transactions and output data.")
    parser.add_argument('token_address', help="The token contract address")
    parser.add_argument('wallet_address', help="The wallet address to fetch transactions for")
    parser.add_argument('--debug', '-d', action='store_true', help="Enable debug mode to print detailed transaction info")

    args = parser.parse_args()

    token_address = args.token_address
    wallet_address = args.wallet_address
    debug_mode = args.debug

    # Fetch enriched transactions with pagination
    transactions = fetch_enriched_transactions(wallet_address)
    processed_data, total_tokens_bought, total_tokens_sold, total_sol_spent, total_sol_received, connected_wallets, first_purchase_date, last_sale_date = process_transactions(transactions, wallet_address, token_address, debug_mode)

    # Save to CSV
    save_to_csv(processed_data)

    # Output summary
    if processed_data:
        print(f"Total Tokens Bought: {total_tokens_bought}")
        print(f"Total SOL Spent: {total_sol_spent}")
        print(f"Total Tokens Sold: {total_tokens_sold}")
        print(f"Total SOL Received: {total_sol_received}")
        print(f"Total Tokens (Bought - Sold): {total_tokens_bought - total_tokens_sold}")
        print(f"Net Total Profit/Loss in SOL: {total_sol_received - total_sol_spent}")
        print(f"Connected Wallets: {', '.join(connected_wallets)}")
        print(f"Date of First Purchase (EST): {first_purchase_date}")
        print(f"Date of Last Sale (EST): {last_sale_date}")
    else:
        print("No transactions found or processed.")

if __name__ == "__main__":
    main()
