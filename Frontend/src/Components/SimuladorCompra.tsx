import { useState } from 'react';
import './SimuladorCompra.css'; 

interface Props {
  onComprar: () => void;
}

export default function SimuladorCompra({ onComprar }: Props) {
  const [amount, setAmount] = useState('');
  const [merchant, setMerchant] = useState('');

  const handlePurchase = (e: React.FormEvent) => {
    e.preventDefault();
    // Salto directo: ejecuta la transición a DecisionPanel de inmediato
    onComprar();
  };

  return (
    <div className="simulador-card">
      <h2 className="simulador-titulo">Checkout</h2>

      <form onSubmit={handlePurchase}>
        <div className="grupo-input">
          <label className="etiqueta">Comercio</label>
          <select 
            required
            value={merchant}
            onChange={(e) => setMerchant(e.target.value)}
            className="campo-texto"
          >
            <option value="" disabled>Selecciona un comercio</option>
            <option value="amazon">Amazon</option>
            <option value="uber">Uber</option>
            <option value="comercio_nuevo_sospechoso">TechStore Desconocida</option>
          </select>
        </div>
        
        <div className="grupo-input">
          <label className="etiqueta">Importe ($)</label>
          <input 
            type="number" 
            required
            min="1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="campo-texto"
            placeholder="Ej. 1500"
          />
        </div>

        <button type="submit" className="btn-comprar">
          Realizar Compra
        </button>
      </form>
    </div>
  );
}