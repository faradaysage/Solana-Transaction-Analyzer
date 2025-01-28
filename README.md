
# Solana Transaction Analyzer

## Description

The Solana Transaction Analyzer is a Python-based tool designed to analyze Solana transactions for a specific wallet and token. It uses the Helius API to fetch enriched transaction data and processes it to extract meaningful insights such as tokens bought/sold, connected wallets, and SOL fees. This project can be extended to include further transaction analytics or customized to suit specific use cases.

---

## Features

- **Transaction Fetching**:
  - Fetches enriched transaction data from the Helius API with pagination support.
  - Supports classification of transactions as swaps, transfers, or other types.

- **Transaction Processing**:
  - Processes token transfers and SOL transfers.
  - Identifies connected wallets and tracks token balances over time.
  - Computes total SOL spent/received, tokens bought/sold, and transaction fees.

- **CSV Output**:
  - Saves processed transaction data into a CSV file for further analysis.

---

## Prerequisites

1. **Python Version**:
   - Requires Python 3.8 or higher.

2. **Python Libraries**:
   Install the required libraries using `pip`:
   ```bash
   pip install requests python-dotenv pytz
   ```

3. **Helius API Key**:
   - Obtain a Helius API key from [Helius](https://www.helius.dev/).
   - Create a `.env` file in the root of the project directory with the following content:
     ```
     HELIUS_API_KEY=YOUR_API_KEY
     ```

---

## Usage

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create and configure the `.env` file:
   ```plaintext
   HELIUS_API_KEY=YOUR_API_KEY
   ```

3. Run the script with the required arguments:
   ```bash
   python script.py <token_address> <wallet_address> [--debug]
   ```
   - `<token_address>`: The token's mint address.
   - `<wallet_address>`: The wallet address to analyze.
   - `--debug` (optional): Enables detailed debugging output.

4. Example:
   ```bash
   python script.py TokenMintAddress WalletAddress --debug
   ```

5. Output:
   - Processed transaction data is saved to a CSV file named `transactions.csv`.

---

## File Structure

- `script.py`: Main script for fetching and analyzing transactions.
- `.env`: Contains the Helius API key (not included in the repository).
- `transactions.csv`: CSV file generated with the processed data.

---

## Future Enhancements

- Add support for additional transaction types.
- Integrate data visualization for transaction analysis.
- Extend compatibility for multi-token analysis.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Acknowledgments

- **Helius API** for providing enriched transaction data.
- Python community for the libraries and tools that made this project possible.
