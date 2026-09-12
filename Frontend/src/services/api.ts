// 1. FUNCIÓN PARA EL SIMULADOR DE COMPRAS
export const evaluarCompra = async (amount: string, merchant: string) => {
  // Simulamos el tiempo de espera de una petición real
  await new Promise(resolve => setTimeout(resolve, 800)); 
  
  const mockAction = Math.random() > 0.5 ? 'allow' : 'verify'; 
  
  return { 
    id: 'txn_' + Math.floor(Math.random() * 100000), 
    action: mockAction 
  };
};

// 2. INTERFAZ Y FUNCIÓN PARA EL FEED RECIENTE
export interface DecisionRecord {
  id: string;
  merchant: string;
  amount: number;
  action: 'allow' | 'verify';
  status: 'SUCCESS' | 'ABANDONED' | 'PENDING';
  timestamp: string;
}

export const obtenerDecisionesRecientes = async (): Promise<DecisionRecord[]> => {
  // Simulamos la latencia de red
  await new Promise(resolve => setTimeout(resolve, 600));

  // Simulamos la respuesta de tu base de datos
  return [
    { id: 'txn_99212', merchant: 'Amazon', amount: 1500, action: 'allow', status: 'SUCCESS', timestamp: 'Hace 2 min' },
    { id: 'txn_88341', merchant: 'TechStore Desconocida', amount: 8500, action: 'verify', status: 'ABANDONED', timestamp: 'Hace 5 min' },
    { id: 'txn_77123', merchant: 'Uber', amount: 150, action: 'allow', status: 'SUCCESS', timestamp: 'Hace 12 min' },
    { id: 'txn_66901', merchant: 'Amazon', amount: 12000, action: 'verify', status: 'SUCCESS', timestamp: 'Hace 1 hora' },
  ];
};