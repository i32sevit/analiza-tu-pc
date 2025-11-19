import React, { useState } from 'react';
import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  TextInput,
  Modal,
  Alert,
  ActivityIndicator,
  Dimensions,
  SafeAreaView,
  StatusBar
} from 'react-native';

const { width: screenWidth } = Dimensions.get('window');

// Servicios simplificados
const API_BASE = 'https://analizatupc-backend.onrender.com';

const authService = {
  async login(username, password) {
    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      
      if (!response.ok) throw new Error('Error en login');
      return await response.json();
    } catch (error) {
      throw new Error('Error en el inicio de sesión');
    }
  },

  async register(username, email, password) {
    try {
      const response = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, email, password }),
      });
      
      if (!response.ok) throw new Error('Error en registro');
      return await response.json();
    } catch (error) {
      throw new Error('Error en el registro');
    }
  },
};

const analysisService = {
  async analyzeSystem(data, token = null) {
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });

      if (response.ok) {
        return await response.json();
      } else {
        // Si falla la API, generar análisis local
        return this.generateLocalAnalysis(data);
      }
    } catch (error) {
      return this.generateLocalAnalysis(data);
    }
  },

  generateLocalAnalysis(data) {
    let baseScore = 50;
    
    if (data.cpu_model && (data.cpu_model.includes('i9') || data.cpu_model.includes('Ryzen 9'))) baseScore += 30;
    else if (data.cpu_model && (data.cpu_model.includes('i7') || data.cpu_model.includes('Ryzen 7'))) baseScore += 20;
    else if (data.cpu_model && (data.cpu_model.includes('i5') || data.cpu_model.includes('Ryzen 5'))) baseScore += 10;
    
    if (data.ram_gb >= 32) baseScore += 20;
    else if (data.ram_gb >= 16) baseScore += 15;
    else if (data.ram_gb >= 8) baseScore += 10;
    
    if (data.disk_type === 'NVMe') baseScore += 15;
    else if (data.disk_type === 'SSD') baseScore += 10;
    
    if (data.gpu_model && (data.gpu_model.includes('RTX 40') || data.gpu_model.includes('RX 7900'))) baseScore += 25;
    else if (data.gpu_model && (data.gpu_model.includes('RTX 30') || data.gpu_model.includes('RX 6000'))) baseScore += 20;
    else if (data.gpu_model && (data.gpu_model.includes('RTX 20') || data.gpu_model.includes('RX 5000'))) baseScore += 15;
    
    baseScore = Math.min(baseScore, 100);
    
    return {
      result: {
        main_profile: baseScore >= 70 ? 'Gaming/Profesional' : baseScore >= 50 ? 'Multimedia' : 'Básico',
        main_score: baseScore,
        scores: {
          'Gaming': Math.min(baseScore + 5, 100),
          'Diseño': Math.min(baseScore + 3, 100),
          'Oficina': Math.min(baseScore + 10, 100),
          'Desarrollo': Math.min(baseScore + 2, 100),
          'Streaming': Math.min(baseScore - 5, 100)
        }
      },
      is_guest: !token
    };
  }
};

// Componente Header
const Header = ({ user, onLogin, onLogout, onHistory }) => (
  <View style={styles.header}>
    <View style={styles.logoContainer}>
      <View style={styles.logoIcon}>
        <Text style={styles.logoText}>💻</Text>
      </View>
      <Text style={styles.title}>AnalizaTuPc</Text>
    </View>
    
    <View style={styles.userBar}>
      {user ? (
        <>
          <TouchableOpacity style={styles.userInfo} onPress={onHistory}>
            <View style={styles.userAvatar}>
              <Text style={styles.avatarText}>
                {user.username?.charAt(0)?.toUpperCase() || 'U'}
              </Text>
            </View>
            <Text style={styles.userName}>{user.username}</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.iconButton} onPress={onHistory}>
            <Text style={styles.iconText}>🕒</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.iconButton} onPress={onLogout}>
            <Text style={styles.iconText}>🚪</Text>
          </TouchableOpacity>
        </>
      ) : (
        <View style={styles.authButtons}>
          <TouchableOpacity style={styles.authButton} onPress={onLogin}>
            <Text style={styles.authButtonText}>Iniciar Sesión</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  </View>
);

// Componente AnalysisCard - SOLO ENTRADA MANUAL
const AnalysisCard = ({ onManualAnalysis, analyzing }) => {
  const [manualData, setManualData] = useState({
    cpu_model: '',
    cpu_speed_ghz: '',
    cores: '',
    ram_gb: '',
    disk_type: 'SSD',
    gpu_model: '',
    gpu_vram_gb: ''
  });

  const handleManualSubmit = () => {
    if (!manualData.cpu_model || !manualData.cpu_speed_ghz || !manualData.cores || !manualData.ram_gb || !manualData.gpu_model) {
      Alert.alert('Error', 'Por favor completa todos los campos obligatorios');
      return;
    }
    onManualAnalysis(manualData);
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardIcon}>
          <Text style={styles.cardIconText}>🚀</Text>
        </View>
        <Text style={styles.cardTitle}>Análisis del Sistema</Text>
      </View>
      
      <ScrollView style={styles.tabContent} showsVerticalScrollIndicator={false}>
        <TextInput
          style={styles.input}
          placeholder="Modelo de CPU (ej: Intel Core i7-13700K)"
          value={manualData.cpu_model}
          onChangeText={(text) => setManualData({...manualData, cpu_model: text})}
          placeholderTextColor="#8b8b9d"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Velocidad de CPU (GHz)"
          value={manualData.cpu_speed_ghz}
          onChangeText={(text) => setManualData({...manualData, cpu_speed_ghz: text})}
          keyboardType="numeric"
          placeholderTextColor="#8b8b9d"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Núcleos de CPU"
          value={manualData.cores}
          onChangeText={(text) => setManualData({...manualData, cores: text})}
          keyboardType="numeric"
          placeholderTextColor="#8b8b9d"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Memoria RAM (GB)"
          value={manualData.ram_gb}
          onChangeText={(text) => setManualData({...manualData, ram_gb: text})}
          keyboardType="numeric"
          placeholderTextColor="#8b8b9d"
        />
        
        <View style={styles.pickerContainer}>
          <Text style={styles.pickerLabel}>Tipo de Almacenamiento</Text>
          <View style={styles.picker}>
            <TouchableOpacity 
              style={[styles.pickerOption, manualData.disk_type === 'SSD' && styles.pickerOptionActive]}
              onPress={() => setManualData({...manualData, disk_type: 'SSD'})}
            >
              <Text style={manualData.disk_type === 'SSD' ? styles.pickerOptionTextActive : styles.pickerOptionText}>
                SSD
              </Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.pickerOption, manualData.disk_type === 'NVMe' && styles.pickerOptionActive]}
              onPress={() => setManualData({...manualData, disk_type: 'NVMe'})}
            >
              <Text style={manualData.disk_type === 'NVMe' ? styles.pickerOptionTextActive : styles.pickerOptionText}>
                NVMe
              </Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.pickerOption, manualData.disk_type === 'HDD' && styles.pickerOptionActive]}
              onPress={() => setManualData({...manualData, disk_type: 'HDD'})}
            >
              <Text style={manualData.disk_type === 'HDD' ? styles.pickerOptionTextActive : styles.pickerOptionText}>
                HDD
              </Text>
            </TouchableOpacity>
          </View>
        </View>
        
        <TextInput
          style={styles.input}
          placeholder="Modelo de GPU (ej: NVIDIA RTX 4070)"
          value={manualData.gpu_model}
          onChangeText={(text) => setManualData({...manualData, gpu_model: text})}
          placeholderTextColor="#8b8b9d"
        />
        
        <TextInput
          style={styles.input}
          placeholder="VRAM de GPU (GB)"
          value={manualData.gpu_vram_gb}
          onChangeText={(text) => setManualData({...manualData, gpu_vram_gb: text})}
          keyboardType="numeric"
          placeholderTextColor="#8b8b9d"
        />
        
        <TouchableOpacity 
          style={styles.btn}
          onPress={handleManualSubmit}
          disabled={analyzing}
        >
          {analyzing ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Text style={styles.btnIcon}>📊</Text>
              <Text style={styles.btnText}>Analizar Mi PC</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
};

// Componente AuthModal (igual que antes)
const AuthModal = ({ visible, onClose, onAuthSuccess }) => {
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    loginUsername: '',
    loginPassword: '',
    registerUsername: '',
    registerEmail: '',
    registerPassword: '',
    registerConfirmPassword: ''
  });

  const handleLogin = async () => {
    if (!formData.loginUsername || !formData.loginPassword) {
      Alert.alert('Error', 'Completa todos los campos');
      return;
    }

    setLoading(true);
    try {
      const result = await authService.login(formData.loginUsername, formData.loginPassword);
      onAuthSuccess(result.user);
      onClose();
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!formData.registerUsername || !formData.registerEmail || !formData.registerPassword) {
      Alert.alert('Error', 'Completa todos los campos');
      return;
    }

    if (formData.registerPassword !== formData.registerConfirmPassword) {
      Alert.alert('Error', 'Las contraseñas no coinciden');
      return;
    }

    setLoading(true);
    try {
      await authService.register(
        formData.registerUsername,
        formData.registerEmail,
        formData.registerPassword
      );
      // Auto-login después del registro
      const result = await authService.login(formData.registerUsername, formData.registerPassword);
      onAuthSuccess(result.user);
      onClose();
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <TouchableOpacity style={styles.modalClose} onPress={onClose}>
            <Text style={styles.modalCloseText}>✕</Text>
          </TouchableOpacity>

          <View style={styles.authTabs}>
            <TouchableOpacity 
              style={[styles.authTab, activeTab === 'login' && styles.authTabActive]}
              onPress={() => setActiveTab('login')}
            >
              <Text style={[styles.authTabText, activeTab === 'login' && styles.authTabTextActive]}>
                Iniciar Sesión
              </Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.authTab, activeTab === 'register' && styles.authTabActive]}
              onPress={() => setActiveTab('register')}
            >
              <Text style={[styles.authTabText, activeTab === 'register' && styles.authTabTextActive]}>
                Registrarse
              </Text>
            </TouchableOpacity>
          </View>

          {activeTab === 'login' && (
            <View style={styles.authForm}>
              <Text style={styles.modalTitle}>Bienvenido de nuevo</Text>
              <Text style={styles.modalSubtitle}>Ingresa a tu cuenta para guardar tu historial</Text>
              
              <TextInput
                style={styles.input}
                placeholder="Usuario"
                value={formData.loginUsername}
                onChangeText={(text) => setFormData({...formData, loginUsername: text})}
                placeholderTextColor="#8b8b9d"
              />
              
              <TextInput
                style={styles.input}
                placeholder="Contraseña"
                value={formData.loginPassword}
                onChangeText={(text) => setFormData({...formData, loginPassword: text})}
                secureTextEntry
                placeholderTextColor="#8b8b9d"
              />
              
              <TouchableOpacity 
                style={styles.btnModal}
                onPress={handleLogin}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnModalText}>Iniciar Sesión</Text>
                )}
              </TouchableOpacity>
              
              <Text style={styles.authFooter}>
                ¿No tienes cuenta?{' '}
                <Text style={styles.authLink} onPress={() => setActiveTab('register')}>
                  Regístrate aquí
                </Text>
              </Text>
            </View>
          )}

          {activeTab === 'register' && (
            <View style={styles.authForm}>
              <Text style={styles.modalTitle}>Crear Cuenta</Text>
              <Text style={styles.modalSubtitle}>Regístrate para guardar tu historial</Text>
              
              <TextInput
                style={styles.input}
                placeholder="Usuario"
                value={formData.registerUsername}
                onChangeText={(text) => setFormData({...formData, registerUsername: text})}
                placeholderTextColor="#8b8b9d"
              />
              
              <TextInput
                style={styles.input}
                placeholder="Email"
                value={formData.registerEmail}
                onChangeText={(text) => setFormData({...formData, registerEmail: text})}
                keyboardType="email-address"
                placeholderTextColor="#8b8b9d"
              />
              
              <TextInput
                style={styles.input}
                placeholder="Contraseña"
                value={formData.registerPassword}
                onChangeText={(text) => setFormData({...formData, registerPassword: text})}
                secureTextEntry
                placeholderTextColor="#8b8b9d"
              />
              
              <TextInput
                style={styles.input}
                placeholder="Confirmar Contraseña"
                value={formData.registerConfirmPassword}
                onChangeText={(text) => setFormData({...formData, registerConfirmPassword: text})}
                secureTextEntry
                placeholderTextColor="#8b8b9d"
              />
              
              <TouchableOpacity 
                style={styles.btnModal}
                onPress={handleRegister}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnModalText}>Crear Cuenta</Text>
                )}
              </TouchableOpacity>
              
              <Text style={styles.authFooter}>
                ¿Ya tienes cuenta?{' '}
                <Text style={styles.authLink} onPress={() => setActiveTab('login')}>
                  Inicia sesión aquí
                </Text>
              </Text>
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
};

// Componente ResultsScreen (igual que antes)
const ResultsScreen = ({ analysisData, analysisResult, onBack }) => {
  const renderProfileCards = () => {
    if (!analysisResult.scores) return null;
    
    return Object.entries(analysisResult.scores).map(([profile, score], index) => (
      <View key={profile} style={styles.profileCard}>
        <Text style={styles.profileName}>{profile}</Text>
        <Text style={styles.profileScore}>{(score * 100).toFixed(1)}%</Text>
        <View style={styles.profileBar}>
          <View style={[styles.profileFill, { width: `${score * 100}%` }]} />
        </View>
      </View>
    ));
  };

  const renderComponentAnalysis = () => {
    const components = [
      {
        name: 'Procesador (CPU)',
        icon: '⚡',
        details: analysisData?.cpu_model || 'N/A',
        score: calculateCPUScore(analysisData)
      },
      {
        name: 'Memoria RAM',
        icon: '🧠',
        details: `${analysisData?.ram_gb || 0} GB`,
        score: calculateRAMScore(analysisData)
      },
      {
        name: 'Almacenamiento',
        icon: '💾',
        details: analysisData?.disk_type || 'N/A',
        score: calculateStorageScore(analysisData)
      },
      {
        name: 'Tarjeta Gráfica (GPU)',
        icon: '🎮',
        details: analysisData?.gpu_model || 'Integrada',
        score: calculateGPUScore(analysisData)
      }
    ];

    return components.map((component, index) => (
      <View key={index} style={styles.componentCard}>
        <View style={styles.componentHeader}>
          <View style={styles.componentIcon}>
            <Text style={styles.componentIconText}>{component.icon}</Text>
          </View>
          <Text style={styles.componentName}>{component.name}</Text>
        </View>
        <Text style={styles.componentDetails}>{component.details}</Text>
        <View style={styles.componentRating}>
          <View style={styles.ratingStars}>
            <Text style={styles.ratingStarsText}>{getStars(component.score / 100)}</Text>
          </View>
          <Text style={styles.ratingText}>{Math.round(component.score)}%</Text>
        </View>
      </View>
    ));
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.resultsHeader}>
        <Text style={styles.resultsTitle}>Resultados del Análisis</Text>
        <Text style={styles.resultsSubtitle}>Evaluación completa del rendimiento de tu sistema</Text>
      </View>

      <View style={styles.scoreDisplay}>
        <View style={styles.scoreCircle}>
          <Text style={styles.scoreValue}>{analysisResult.main_score}%</Text>
        </View>
        <Text style={styles.scoreLabel}>{analysisResult.main_profile}</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Rendimiento por Perfil</Text>
        <View style={styles.profileGrid}>
          {renderProfileCards()}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Análisis por Componente</Text>
        <View style={styles.componentGrid}>
          {renderComponentAnalysis()}
        </View>
      </View>

      <View style={styles.recommendations}>
        <Text style={styles.recommendationsTitle}>
          <Text style={styles.recommendationsIcon}>💡</Text> Recomendaciones de Mejora
        </Text>
        <View style={styles.recommendationItem}>
          <Text style={styles.recommendationIcon}>✅</Text>
          <Text style={styles.recommendationText}>
            Mantén tus controladores actualizados para el mejor rendimiento
          </Text>
        </View>
        <View style={styles.recommendationItem}>
          <Text style={styles.recommendationIcon}>✅</Text>
          <Text style={styles.recommendationText}>
            Realiza mantenimiento regular del sistema para mantener el rendimiento
          </Text>
        </View>
        <View style={styles.recommendationItem}>
          <Text style={styles.recommendationIcon}>✅</Text>
          <Text style={styles.recommendationText}>
            Considera actualizar componentes según tus necesidades específicas
          </Text>
        </View>
      </View>

      <TouchableOpacity style={styles.btn} onPress={onBack}>
        <Text style={styles.btnIcon}>⬅️</Text>
        <Text style={styles.btnText}>Volver al Análisis</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

// Funciones auxiliares para cálculos (igual que antes)
const calculateCPUScore = (data) => {
  let score = 50;
  if (data?.cpu_model?.includes('i9') || data?.cpu_model?.includes('Ryzen 9')) score += 35;
  else if (data?.cpu_model?.includes('i7') || data?.cpu_model?.includes('Ryzen 7')) score += 25;
  else if (data?.cpu_model?.includes('i5') || data?.cpu_model?.includes('Ryzen 5')) score += 15;
  
  if (data?.cpu_speed_ghz > 4.0) score += 10;
  if (data?.cores >= 8) score += 10;
  
  return Math.min(score, 100);
};

const calculateRAMScore = (data) => {
  const ram = data?.ram_gb || 0;
  if (ram >= 32) return 100;
  if (ram >= 16) return 85;
  if (ram >= 8) return 70;
  if (ram >= 4) return 50;
  return 30;
};

const calculateStorageScore = (data) => {
  if (data?.disk_type === 'NVMe') return 95;
  if (data?.disk_type === 'SSD') return 80;
  return 50; // HDD
};

const calculateGPUScore = (data) => {
  let score = 50;
  if (data?.gpu_model?.includes('RTX 40') || data?.gpu_model?.includes('RX 7900')) score += 40;
  else if (data?.gpu_model?.includes('RTX 30') || data?.gpu_model?.includes('RX 6000')) score += 30;
  else if (data?.gpu_model?.includes('RTX 20') || data?.gpu_model?.includes('RX 5000')) score += 20;
  
  if (data?.gpu_vram_gb >= 8) score += 10;
  else if (data?.gpu_vram_gb >= 4) score += 5;
  
  return Math.min(score, 100);
};

const getStars = (score) => {
  const fullStars = Math.floor(score * 5);
  const emptyStars = 5 - fullStars;
  
  let stars = '';
  for (let i = 0; i < fullStars; i++) {
    stars += '★';
  }
  for (let i = 0; i < emptyStars; i++) {
    stars += '☆';
  }
  
  return stars;
};

// Estilos (igual que antes)
const styles = {
  container: {
    flex: 1,
    backgroundColor: '#0a0f1f',
  },
  scrollContainer: {
    flexGrow: 1,
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 30,
    paddingTop: 20,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoIcon: {
    width: 50,
    height: 50,
    borderRadius: 12,
    backgroundColor: 'rgba(76,201,240,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  logoText: {
    fontSize: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#4cc9f0',
  },
  userBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    padding: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  userAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#4cc9f0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  avatarText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  userName: {
    color: '#e0e0e0',
    fontSize: 14,
    fontWeight: '500',
  },
  iconButton: {
    padding: 8,
  },
  iconText: {
    fontSize: 18,
  },
  authButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  authButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(76,201,240,0.1)',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  authButtonText: {
    color: '#e0e0e0',
    fontSize: 14,
    fontWeight: '500',
  },
  card: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 20,
    padding: 25,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 25,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  cardIcon: {
    width: 50,
    height: 50,
    borderRadius: 12,
    backgroundColor: 'rgba(76,201,240,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 15,
  },
  cardIconText: {
    fontSize: 20,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#e0e0e0',
  },
  tabContent: {
    minHeight: 200,
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4cc9f0',
    padding: 18,
    borderRadius: 14,
    gap: 12,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnIcon: {
    fontSize: 18,
  },
  btnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  input: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 10,
    padding: 15,
    color: '#e0e0e0',
    marginBottom: 15,
    fontSize: 16,
  },
  pickerContainer: {
    marginBottom: 15,
  },
  pickerLabel: {
    color: '#e0e0e0',
    marginBottom: 8,
    fontWeight: '500',
    fontSize: 14,
  },
  picker: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 10,
    padding: 4,
  },
  pickerOption: {
    flex: 1,
    padding: 12,
    alignItems: 'center',
    borderRadius: 8,
  },
  pickerOptionActive: {
    backgroundColor: 'rgba(76,201,240,0.2)',
  },
  pickerOptionText: {
    color: '#8b8b9d',
    fontSize: 14,
  },
  pickerOptionTextActive: {
    color: '#4cc9f0',
    fontWeight: '500',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(10,15,31,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 30,
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  modalClose: {
    position: 'absolute',
    top: 15,
    right: 15,
    zIndex: 1,
  },
  modalCloseText: {
    fontSize: 20,
    color: '#8b8b9d',
    fontWeight: 'bold',
  },
  authTabs: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 12,
    padding: 4,
    marginBottom: 25,
  },
  authTab: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  authTabActive: {
    backgroundColor: 'rgba(76,201,240,0.2)',
  },
  authTabText: {
    color: '#8b8b9d',
    fontWeight: '500',
    fontSize: 14,
  },
  authTabTextActive: {
    color: '#4cc9f0',
  },
  authForm: {
    minHeight: 300,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#e0e0e0',
    textAlign: 'center',
    marginBottom: 10,
  },
  modalSubtitle: {
    color: '#8b8b9d',
    textAlign: 'center',
    marginBottom: 25,
    fontSize: 14,
  },
  btnModal: {
    backgroundColor: '#4cc9f0',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 15,
  },
  btnModalText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  authFooter: {
    color: '#8b8b9d',
    textAlign: 'center',
    fontSize: 14,
  },
  authLink: {
    color: '#4cc9f0',
  },
  resultsHeader: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: 'rgba(76,201,240,0.1)',
    borderRadius: 16,
    margin: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  resultsTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4cc9f0',
    marginBottom: 10,
    textAlign: 'center',
  },
  resultsSubtitle: {
    color: '#8b8b9d',
    fontSize: 16,
    textAlign: 'center',
  },
  scoreDisplay: {
    alignItems: 'center',
    margin: 30,
  },
  scoreCircle: {
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: 'rgba(76,201,240,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#4cc9f0',
  },
  scoreValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#4cc9f0',
  },
  scoreLabel: {
    color: '#8b8b9d',
    fontSize: 16,
    marginTop: 10,
  },
  section: {
    marginHorizontal: 20,
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#e0e0e0',
    marginBottom: 15,
    textAlign: 'center',
  },
  profileGrid: {
    gap: 15,
  },
  profileCard: {
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  profileName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e0e0e0',
    marginBottom: 10,
  },
  profileScore: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4cc9f0',
    marginBottom: 10,
  },
  profileBar: {
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  profileFill: {
    height: '100%',
    backgroundColor: '#4cc9f0',
    borderRadius: 4,
  },
  componentGrid: {
    gap: 15,
  },
  componentCard: {
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  componentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  componentIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: 'rgba(76,201,240,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  componentIconText: {
    fontSize: 18,
  },
  componentName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e0e0e0',
  },
  componentDetails: {
    color: '#8b8b9d',
    fontSize: 14,
    marginBottom: 15,
  },
  componentRating: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  ratingStars: {
    flexDirection: 'row',
  },
  ratingStarsText: {
    color: '#f72585',
    fontSize: 16,
  },
  ratingText: {
    color: '#8b8b9d',
    fontSize: 14,
  },
  recommendations: {
    backgroundColor: 'rgba(0,245,212,0.1)',
    borderRadius: 16,
    padding: 20,
    margin: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  recommendationsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#e0e0e0',
    marginBottom: 15,
    flexDirection: 'row',
    alignItems: 'center',
  },
  recommendationsIcon: {
    marginRight: 8,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  recommendationIcon: {
    marginRight: 10,
    fontSize: 16,
  },
  recommendationText: {
    color: '#e0e0e0',
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
};

// Componente principal
export default function App() {
  const [currentScreen, setCurrentScreen] = useState('home');
  const [user, setUser] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleManualAnalysis = async (data) => {
    setAnalyzing(true);
    
    try {
      const result = await analysisService.analyzeSystem(data, user?.token);
      setAnalyzing(false);
      setAnalysisData(data);
      setAnalysisResult(result.result || result);
      setCurrentScreen('results');
    } catch (error) {
      setAnalyzing(false);
      Alert.alert('Error', 'No se pudo completar el análisis');
    }
  };

  const handleAuthSuccess = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    setUser(null);
  };

  if (currentScreen === 'results') {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <ResultsScreen
          analysisData={analysisData}
          analysisResult={analysisResult}
          onBack={() => setCurrentScreen('home')}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Header 
          user={user}
          onLogin={() => setShowAuthModal(true)}
          onLogout={handleLogout}
          onHistory={() => Alert.alert('Historial', 'Funcionalidad en desarrollo')}
        />
        
        <AnalysisCard
          onManualAnalysis={handleManualAnalysis}
          analyzing={analyzing}
        />
      </ScrollView>

      <AuthModal
        visible={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </SafeAreaView>
  );
}