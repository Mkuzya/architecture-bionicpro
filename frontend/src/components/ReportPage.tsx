import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface ReportData {
  summary: {
    user_id: string;
    total_records: number;
    total_movements: number;
    avg_response_time: number;
    total_usage_hours: number;
    total_errors: number;
    protheses: string[];
  };
  data: Array<{
    user_id: string;
    date: string;
    customer_name: string;
    customer_email: string;
    prothesis_id: string;
    total_movements: number;
    avg_response_time_ms: number;
    battery_usage_percent: number;
    battery_cycles: number;
    error_count: number;
    usage_hours: number;
    last_activity: string;
  }>;
  generated_at: string;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ReportData | null>(null);

  const downloadReport = async (format: 'json' | 'csv' = 'json') => {
    if (!keycloak?.token) {
      setError('Не аутентифицирован');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports?format=${format}`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Неизвестная ошибка' }));
        throw new Error(errorData.error || errorData.message || `HTTP ${response.status}`);
      }

      if (format === 'csv') {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const data: ReportData = await response.json();
        setReportData(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
      setReportData(null);
    } finally {
      setLoading(false);
    }
  };

  const downloadReportAsJSON = () => {
    if (reportData) {
      const dataStr = JSON.stringify(reportData, null, 2);
      const blob = new Blob([dataStr], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  };

  if (!initialized) {
    return <div>Загрузка...</div>;
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Войти
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8">
          <h1 className="text-3xl font-bold mb-6 text-gray-800">Отчёты об использовании</h1>
          
          <div className="mb-6 flex gap-4">
            <button
              onClick={() => downloadReport('json')}
              disabled={loading}
              className={`px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? 'Загрузка...' : 'Загрузить отчёт'}
            </button>
            
            <button
              onClick={() => downloadReport('csv')}
              disabled={loading}
              className={`px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? 'Скачивание...' : 'Скачать CSV'}
            </button>

            {reportData && (
              <button
                onClick={downloadReportAsJSON}
                className="px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
              >
                Скачать JSON
              </button>
            )}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
              <strong>Ошибка:</strong> {error}
            </div>
          )}

          {reportData && (
            <div className="space-y-6">
              <div className="bg-blue-50 rounded-lg p-6">
                <h2 className="text-2xl font-semibold mb-4 text-gray-800">Сводка отчёта</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">ID пользователя</p>
                    <p className="text-lg font-semibold">{reportData.summary.user_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Всего записей</p>
                    <p className="text-lg font-semibold">{reportData.summary.total_records}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Всего движений</p>
                    <p className="text-lg font-semibold">{reportData.summary.total_movements.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Среднее время отклика</p>
                    <p className="text-lg font-semibold">{reportData.summary.avg_response_time.toFixed(2)} мс</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Всего часов использования</p>
                    <p className="text-lg font-semibold">{reportData.summary.total_usage_hours.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Всего ошибок</p>
                    <p className="text-lg font-semibold">{reportData.summary.total_errors}</p>
                  </div>
                </div>
                {reportData.summary.protheses.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-600">Протезы</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {reportData.summary.protheses.map((prosthesis, idx) => (
                        <span key={idx} className="px-3 py-1 bg-blue-200 text-blue-800 rounded-full text-sm">
                          {prosthesis}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div>
                <h2 className="text-2xl font-semibold mb-4 text-gray-800">Детальные данные</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Дата</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Протез</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Движения</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Время отклика</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Батарея</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Часы использования</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ошибки</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {reportData.data.map((row, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.date}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.prothesis_id}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.total_movements}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.avg_response_time_ms.toFixed(2)} мс</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.battery_usage_percent.toFixed(1)}%</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.usage_hours.toFixed(2)}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.error_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="text-sm text-gray-500">
                Сгенерировано: {new Date(reportData.generated_at).toLocaleString('ru-RU')}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportPage;