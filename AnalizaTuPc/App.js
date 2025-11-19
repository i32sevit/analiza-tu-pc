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

// Servicios
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
        return this.generateLocalAnalysis(data);
      }
    } catch (error) {
      return this.generateLocalAnalysis(data);
    }
  },

  generateLocalAnalysis(data) {
    let baseScore = 50;
    
    // CPU Model Scoring
    if (data.cpu_model && (data.cpu_model.includes('i9') || data.cpu_model.includes('Ryzen 9'))) baseScore += 30;
    else if (data.cpu_model && (data.cpu_model.includes('i7') || data.cpu_model.includes('Ryzen 7'))) baseScore += 20;
    else if (data.cpu_model && (data.cpu_model.includes('i5') || data.cpu_model.includes('Ryzen 5'))) baseScore += 10;
    else if (data.cpu_model && (data.cpu_model.includes('i3') || data.cpu_model.includes('Ryzen 3'))) baseScore += 5;
    
    // CPU Speed Scoring
    const cpuSpeed = parseFloat(data.cpu_speed_ghz) || 0;
    if (cpuSpeed >= 4.5) baseScore += 15;
    else if (cpuSpeed >= 3.5) baseScore += 10;
    else if (cpuSpeed >= 2.5) baseScore += 5;
    
    // Cores Scoring
    const cores = parseInt(data.cores) || 0;
    if (cores >= 16) baseScore += 20;
    else if (cores >= 12) baseScore += 15;
    else if (cores >= 8) baseScore += 10;
    else if (cores >= 6) baseScore += 5;
    else if (cores >= 4) baseScore += 2;
    
    // RAM Scoring
    const ram = parseInt(data.ram_gb) || 0;
    if (ram >= 32) baseScore += 20;
    else if (ram >= 16) baseScore += 15;
    else if (ram >= 8) baseScore += 10;
    else if (ram >= 4) baseScore += 5;
    
    // Storage Scoring
    if (data.disk_type === 'NVMe') baseScore += 15;
    else if (data.disk_type === 'SSD') baseScore += 10;
    else if (data.disk_type === 'HDD') baseScore += 0;
    
    // GPU Scoring
    if (data.gpu_model && (data.gpu_model.includes('RTX 40') || data.gpu_model.includes('RX 7900'))) baseScore += 25;
    else if (data.gpu_model && (data.gpu_model.includes('RTX 30') || data.gpu_model.includes('RX 6000'))) baseScore += 20;
    else if (data.gpu_model && (data.gpu_model.includes('RTX 20') || data.gpu_model.includes('RX 5000'))) baseScore += 15;
    else if (data.gpu_model && (data.gpu_model.includes('GTX 16') || data.gpu_model.includes('RX 500'))) baseScore += 10;
    else if (data.gpu_model && (data.gpu_model.includes('GTX 10') || data.gpu_model.includes('RX 400'))) baseScore += 5;
    
    // VRAM Scoring
    const vram = parseInt(data.gpu_vram_gb) || 0;
    if (vram >= 12) baseScore += 10;
    else if (vram >= 8) baseScore += 7;
    else if (vram >= 6) baseScore += 5;
    else if (vram >= 4) baseScore += 3;
    else if (vram >= 2) baseScore += 1;
    
    // Asegurar que el score esté entre 0 y 100
    baseScore = Math.max(0, Math.min(baseScore, 100));
    
    // Calcular scores específicos por categoría
    const calculateCategoryScore = (base, multiplier, bonus = 0) => {
      let score = base * multiplier + bonus;
      return Math.max(0, Math.min(Math.round(score), 100));
    };
    
    return {
      result: {
        main_profile: baseScore >= 80 ? 'Gaming/Profesional' : baseScore >= 60 ? 'Multimedia' : baseScore >= 40 ? 'Oficina' : 'Básico',
        main_score: Math.round(baseScore),
        scores: {
          'Gaming': calculateCategoryScore(baseScore, 1.0, 
            (data.gpu_model && data.gpu_model.includes('RTX')) ? 10 : 
            (data.gpu_model && data.gpu_model.includes('RX')) ? 8 : 0),
          'Edición Video': calculateCategoryScore(baseScore, 0.9, 
            (ram >= 16) ? 15 : (ram >= 8) ? 8 : 0),
          'Ofimática': calculateCategoryScore(baseScore, 1.2, 
            (cpuSpeed >= 3.0) ? 10 : 5),
          'Virtualización': calculateCategoryScore(baseScore, 0.95, 
            (cores >= 8) ? 12 : (cores >= 4) ? 6 : 0),
          'ML Ligero': calculateCategoryScore(baseScore, 0.85, 
            (data.gpu_model && (data.gpu_model.includes('RTX 30') || data.gpu_model.includes('RTX 40'))) ? 15 : 0)
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

// Componente CustomPicker
const CustomPicker = ({ 
  label, 
  selectedValue, 
  onValueChange, 
  items, 
  placeholder = "Seleccionar..." 
}) => {
  const [showDropdown, setShowDropdown] = useState(false);

  const selectedItem = items.find(item => item.value === selectedValue);

  return (
    <View style={styles.pickerContainer}>
      <Text style={styles.pickerLabel}>{label}</Text>
      <TouchableOpacity 
        style={styles.customPicker}
        onPress={() => setShowDropdown(true)}
      >
        <Text style={selectedValue ? styles.pickerSelectedText : styles.pickerPlaceholderText}>
          {selectedItem ? selectedItem.label : placeholder}
        </Text>
        <Text style={styles.pickerArrow}>▼</Text>
      </TouchableOpacity>

      <Modal
        visible={showDropdown}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowDropdown(false)}
      >
        <TouchableOpacity 
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowDropdown(false)}
        >
          <View style={styles.dropdownModalContainer}>
            <View style={styles.dropdownModalContent}>
              <Text style={styles.dropdownTitle}>{label}</Text>
              <ScrollView 
                style={styles.dropdownScroll}
                showsVerticalScrollIndicator={false}
              >
                {items.map((item, index) => (
                  <TouchableOpacity
                    key={index}
                    style={[
                      styles.dropdownItem,
                      selectedValue === item.value && styles.dropdownItemSelected
                    ]}
                    onPress={() => {
                      onValueChange(item.value);
                      setShowDropdown(false);
                    }}
                  >
                    <Text style={[
                      styles.dropdownItemText,
                      selectedValue === item.value && styles.dropdownItemTextSelected
                    ]}>
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TouchableOpacity 
                style={styles.dropdownCloseButton}
                onPress={() => setShowDropdown(false)}
              >
                <Text style={styles.dropdownCloseText}>Cerrar</Text>
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
};

// Componente AuthModal
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

// Componente ResultsScreen CORREGIDO
const ResultsScreen = ({ analysisData, analysisResult, onBack }) => {
  const getScoreColor = (score) => {
    if (score >= 80) return '#4ade80';
    if (score >= 60) return '#fbbf24';
    if (score >= 40) return '#fb923c';
    return '#f87171';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Excelente';
    if (score >= 60) return 'Bueno';
    if (score >= 40) return 'Regular';
    return 'Básico';
  };

  // Convertir scores decimales a porcentajes enteros si es necesario
  const formatScore = (score) => {
    if (score <= 1) {
      return Math.round(score * 100);
    }
    return Math.round(score);
  };

  // Mapear categorías a nombres consistentes
  const categoryMap = {
    'Gaming': 'Gaming',
    'Diseño': 'Edición Video',
    'Oficina': 'Ofimática',
    'Desarrollo': 'Virtualización',
    'Streaming': 'ML Ligero'
  };

  return (
    <View style={styles.resultsContainer}>
      <View style={styles.resultsHeader}>
        <TouchableOpacity style={styles.backButton} onPress={onBack}>
          <Text style={styles.backButtonText}>← Volver</Text>
        </TouchableOpacity>
        <Text style={styles.resultsTitle}>Resultados del Análisis</Text>
        <View style={{ width: 80 }} />
      </View>

      <ScrollView style={styles.resultsContent}>
        {/* Tarjeta de Puntuación Principal */}
        <View style={styles.mainScoreCard}>
          <View style={styles.scoreCircle}>
            <Text style={styles.mainScore}>{formatScore(analysisResult.main_score)}</Text>
            <Text style={styles.scoreLabel}>Puntuación</Text>
          </View>
          <View style={styles.profileInfo}>
            <Text style={styles.profileTitle}>Perfil Principal</Text>
            <Text style={styles.profileValue}>{analysisResult.main_profile}</Text>
            <View style={[
              styles.scoreBadge,
              { backgroundColor: getScoreColor(formatScore(analysisResult.main_score)) }
            ]}>
              <Text style={styles.scoreBadgeText}>
                {getScoreLabel(formatScore(analysisResult.main_score))}
              </Text>
            </View>
          </View>
        </View>

        {/* Especificaciones del Sistema */}
        <View style={styles.specsCard}>
          <Text style={styles.sectionTitle}>Especificaciones Analizadas</Text>
          <View style={styles.specsGrid}>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>CPU</Text>
              <Text style={styles.specValue}>{analysisData.cpu_model}</Text>
            </View>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>Velocidad</Text>
              <Text style={styles.specValue}>{analysisData.cpu_speed_ghz} GHz</Text>
            </View>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>Núcleos</Text>
              <Text style={styles.specValue}>{analysisData.cores}</Text>
            </View>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>RAM</Text>
              <Text style={styles.specValue}>{analysisData.ram_gb} GB</Text>
            </View>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>Almacenamiento</Text>
              <Text style={styles.specValue}>{analysisData.disk_type}</Text>
            </View>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>GPU</Text>
              <Text style={styles.specValue}>{analysisData.gpu_model}</Text>
            </View>
          </View>
        </View>

        {/* Puntuaciones por Categoría - COMPLETAMENTE CORREGIDO */}
        <View style={styles.scoresCard}>
          <Text style={styles.sectionTitle}>Rendimiento por Actividad</Text>
          <View style={styles.scoresList}>
            {Object.entries(analysisResult.scores || {}).map(([category, score]) => {
              const formattedScore = formatScore(score);
              const displayCategory = categoryMap[category] || category;
              
              return (
                <View key={category} style={styles.scoreRow}>
                  <Text style={styles.scoreCategory}>{displayCategory}</Text>
                  <View style={styles.scoreBarContainer}>
                    <View 
                      style={[
                        styles.scoreBar, 
                        { 
                          width: `${formattedScore}%`,
                          backgroundColor: getScoreColor(formattedScore)
                        }
                      ]} 
                    />
                  </View>
                  <Text style={[styles.scoreValue, { color: getScoreColor(formattedScore) }]}>
                    {formattedScore}
                  </Text>
                </View>
              );
            })}
          </View>
        </View>

        {/* Recomendaciones */}
        <View style={styles.recommendationsCard}>
          <Text style={styles.sectionTitle}>Recomendaciones</Text>
          <View style={styles.recommendationsList}>
            {formatScore(analysisResult.main_score) < 60 && (
              <View style={styles.recommendationItem}>
                <Text style={styles.recommendationIcon}>💡</Text>
                <Text style={styles.recommendationText}>
                  Considera actualizar tu hardware para mejor rendimiento
                </Text>
              </View>
            )}
            {parseInt(analysisData.ram_gb) < 16 && (
              <View style={styles.recommendationItem}>
                <Text style={styles.recommendationIcon}>🧠</Text>
                <Text style={styles.recommendationText}>
                  Aumentar la RAM mejoraría el rendimiento multitarea
                </Text>
              </View>
            )}
            {analysisData.disk_type === 'HDD' && (
              <View style={styles.recommendationItem}>
                <Text style={styles.recommendationIcon}>⚡</Text>
                <Text style={styles.recommendationText}>
                  Un SSD mejoraría significativamente los tiempos de carga
                </Text>
              </View>
            )}
            <View style={styles.recommendationItem}>
              <Text style={styles.recommendationIcon}>🔧</Text>
              <Text style={styles.recommendationText}>
                Mantén tus drivers actualizados para óptimo rendimiento
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </View>
  );
};

// AnalysisCard
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

  // Opciones
  const cpuOptions = [
    { label: 'Intel Core i3-10100', value: 'Intel Core i3-10100' },
    { label: 'Intel Core i5-10400', value: 'Intel Core i5-10400' },
    { label: 'Intel Core i7-10700', value: 'Intel Core i7-10700' },
    { label: 'Intel Core i9-10900', value: 'Intel Core i9-10900' },
    { label: 'Intel Core i3-12100', value: 'Intel Core i3-12100' },
    { label: 'Intel Core i5-12400', value: 'Intel Core i5-12400' },
    { label: 'Intel Core i7-12700', value: 'Intel Core i7-12700' },
    { label: 'Intel Core i9-12900', value: 'Intel Core i9-12900' },
    { label: 'Intel Core i5-13600K', value: 'Intel Core i5-13600K' },
    { label: 'Intel Core i7-13700K', value: 'Intel Core i7-13700K' },
    { label: 'Intel Core i9-13900K', value: 'Intel Core i9-13900K' },
    { label: 'AMD Ryzen 3 3100', value: 'AMD Ryzen 3 3100' },
    { label: 'AMD Ryzen 5 3600', value: 'AMD Ryzen 5 3600' },
    { label: 'AMD Ryzen 7 3700X', value: 'AMD Ryzen 7 3700X' },
    { label: 'AMD Ryzen 9 3900X', value: 'AMD Ryzen 9 3900X' },
    { label: 'AMD Ryzen 5 5600X', value: 'AMD Ryzen 5 5600X' },
    { label: 'AMD Ryzen 7 5800X', value: 'AMD Ryzen 7 5800X' },
    { label: 'AMD Ryzen 9 5900X', value: 'AMD Ryzen 9 5900X' },
    { label: 'AMD Ryzen 9 5950X', value: 'AMD Ryzen 9 5950X' },
    { label: 'AMD Ryzen 5 7600X', value: 'AMD Ryzen 5 7600X' },
    { label: 'AMD Ryzen 7 7700X', value: 'AMD Ryzen 7 7700X' },
    { label: 'AMD Ryzen 9 7900X', value: 'AMD Ryzen 9 7900X' },
    { label: 'AMD Ryzen 9 7950X', value: 'AMD Ryzen 9 7950X' }
  ];

  const gpuOptions = [
    { label: 'NVIDIA GeForce GTX 1650', value: 'NVIDIA GeForce GTX 1650' },
    { label: 'NVIDIA GeForce GTX 1660', value: 'NVIDIA GeForce GTX 1660' },
    { label: 'NVIDIA GeForce RTX 2060', value: 'NVIDIA GeForce RTX 2060' },
    { label: 'NVIDIA GeForce RTX 3060', value: 'NVIDIA GeForce RTX 3060' },
    { label: 'NVIDIA GeForce RTX 3060 Ti', value: 'NVIDIA GeForce RTX 3060 Ti' },
    { label: 'NVIDIA GeForce RTX 3070', value: 'NVIDIA GeForce RTX 3070' },
    { label: 'NVIDIA GeForce RTX 3070 Ti', value: 'NVIDIA GeForce RTX 3070 Ti' },
    { label: 'NVIDIA GeForce RTX 3080', value: 'NVIDIA GeForce RTX 3080' },
    { label: 'NVIDIA GeForce RTX 3080 Ti', value: 'NVIDIA GeForce RTX 3080 Ti' },
    { label: 'NVIDIA GeForce RTX 3090', value: 'NVIDIA GeForce RTX 3090' },
    { label: 'NVIDIA GeForce RTX 3090 Ti', value: 'NVIDIA GeForce RTX 3090 Ti' },
    { label: 'NVIDIA GeForce RTX 4060', value: 'NVIDIA GeForce RTX 4060' },
    { label: 'NVIDIA GeForce RTX 4060 Ti', value: 'NVIDIA GeForce RTX 4060 Ti' },
    { label: 'NVIDIA GeForce RTX 4070', value: 'NVIDIA GeForce RTX 4070' },
    { label: 'NVIDIA GeForce RTX 4070 Ti', value: 'NVIDIA GeForce RTX 4070 Ti' },
    { label: 'NVIDIA GeForce RTX 4080', value: 'NVIDIA GeForce RTX 4080' },
    { label: 'NVIDIA GeForce RTX 4090', value: 'NVIDIA GeForce RTX 4090' },
    { label: 'AMD Radeon RX 5500 XT', value: 'AMD Radeon RX 5500 XT' },
    { label: 'AMD Radeon RX 5600 XT', value: 'AMD Radeon RX 5600 XT' },
    { label: 'AMD Radeon RX 5700 XT', value: 'AMD Radeon RX 5700 XT' },
    { label: 'AMD Radeon RX 6600 XT', value: 'AMD Radeon RX 6600 XT' },
    { label: 'AMD Radeon RX 6700 XT', value: 'AMD Radeon RX 6700 XT' },
    { label: 'AMD Radeon RX 6800 XT', value: 'AMD Radeon RX 6800 XT' },
    { label: 'AMD Radeon RX 6900 XT', value: 'AMD Radeon RX 6900 XT' },
    { label: 'AMD Radeon RX 7600', value: 'AMD Radeon RX 7600' },
    { label: 'AMD Radeon RX 7700 XT', value: 'AMD Radeon RX 7700 XT' },
    { label: 'AMD Radeon RX 7800 XT', value: 'AMD Radeon RX 7800 XT' },
    { label: 'AMD Radeon RX 7900 XT', value: 'AMD Radeon RX 7900 XT' },
    { label: 'AMD Radeon RX 7900 XTX', value: 'AMD Radeon RX 7900 XTX' },
    { label: 'Intel Arc A380', value: 'Intel Arc A380' },
    { label: 'Intel Arc A750', value: 'Intel Arc A750' },
    { label: 'Intel Arc A770', value: 'Intel Arc A770' }
  ];

  const ramOptions = [
    { label: '4 GB', value: '4' },
    { label: '8 GB', value: '8' },
    { label: '16 GB', value: '16' },
    { label: '32 GB', value: '32' },
    { label: '64 GB', value: '64' },
    { label: '128 GB', value: '128' }
  ];

  const vramOptions = [
    { label: '2 GB', value: '2' },
    { label: '4 GB', value: '4' },
    { label: '6 GB', value: '6' },
    { label: '8 GB', value: '8' },
    { label: '12 GB', value: '12' },
    { label: '16 GB', value: '16' },
    { label: '24 GB', value: '24' }
  ];

  const diskOptions = [
    { label: 'HDD', value: 'HDD' },
    { label: 'SSD SATA', value: 'SSD' },
    { label: 'NVMe PCIe 3.0', value: 'NVMe' },
    { label: 'NVMe PCIe 4.0', value: 'NVMe' },
    { label: 'NVMe PCIe 5.0', value: 'NVMe' }
  ];

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
      
      <View style={styles.tabContent}>
        <ScrollView 
          style={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          nestedScrollEnabled={true}
        >
          {/* CPU Model */}
          <CustomPicker
            label="Modelo de CPU *"
            selectedValue={manualData.cpu_model}
            onValueChange={(value) => setManualData({...manualData, cpu_model: value})}
            items={cpuOptions}
            placeholder="Selecciona tu procesador"
          />
          
          {/* CPU Speed - AHORA EN LÍNEA COMPLETA */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Velocidad CPU (GHz) *</Text>
            <TextInput
              style={styles.input}
              placeholder="ej: 3.5"
              value={manualData.cpu_speed_ghz}
              onChangeText={(text) => {
                const normalizedText = text.replace(',', '.');
                setManualData({...manualData, cpu_speed_ghz: normalizedText});
              }}
              keyboardType="numeric"
              placeholderTextColor="#8b8b9d"
            />
          </View>

          {/* Núcleos - AHORA EN LÍNEA COMPLETA */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Núcleos *</Text>
            <TextInput
              style={styles.input}
              placeholder="ej: 6"
              value={manualData.cores}
              onChangeText={(text) => setManualData({...manualData, cores: text})}
              keyboardType="numeric"
              placeholderTextColor="#8b8b9d"
            />
          </View>

          {/* RAM */}
          <CustomPicker
            label="Memoria RAM *"
            selectedValue={manualData.ram_gb}
            onValueChange={(value) => setManualData({...manualData, ram_gb: value})}
            items={ramOptions}
            placeholder="Selecciona la RAM"
          />

          {/* Storage Type */}
          <CustomPicker
            label="Tipo de Almacenamiento"
            selectedValue={manualData.disk_type}
            onValueChange={(value) => setManualData({...manualData, disk_type: value})}
            items={diskOptions}
            placeholder="Selecciona el tipo"
          />

          {/* GPU Model */}
          <CustomPicker
            label="Modelo de GPU *"
            selectedValue={manualData.gpu_model}
            onValueChange={(value) => setManualData({...manualData, gpu_model: value})}
            items={gpuOptions}
            placeholder="Selecciona tu tarjeta gráfica"
          />

          {/* VRAM */}
          <CustomPicker
            label="VRAM de GPU"
            selectedValue={manualData.gpu_vram_gb}
            onValueChange={(value) => setManualData({...manualData, gpu_vram_gb: value})}
            items={vramOptions}
            placeholder="Selecciona la VRAM"
          />
          
          <TouchableOpacity 
            style={[styles.btn, analyzing && styles.btnDisabled]}
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
    </View>
  );
};

// ESTILOS
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
    flex: 1,
  },
  scrollContent: {
    flex: 1,
  },
  inputRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
    gap: 10,
    alignItems: 'flex-start',
  },
  inputHalf: {
    flex: 1,
  },
  label: {
    color: '#e0e0e0',
    marginBottom: 8,
    fontWeight: '500',
    fontSize: 14,
  },
  input: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 10,
    padding: 15,
    color: '#e0e0e0',
    fontSize: 16,
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4cc9f0',
    padding: 18,
    borderRadius: 14,
    gap: 12,
    marginTop: 10,
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
  pickerContainer: {
    marginBottom: 15,
  },
  pickerLabel: {
    color: '#e0e0e0',
    marginBottom: 8,
    fontWeight: '500',
    fontSize: 14,
  },
  customPicker: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    borderWidth: 2,
    borderColor: '#4cc9f0',
    borderRadius: 10,
    padding: 15,
  },
  pickerSelectedText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '500',
  },
  pickerPlaceholderText: {
    color: '#8b8b9d',
    fontSize: 16,
  },
  pickerArrow: {
    color: '#4cc9f0',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 10,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  dropdownModalContainer: {
    width: '100%',
    maxWidth: 400,
    maxHeight: '80%',
  },
  dropdownModalContent: {
    backgroundColor: '#1a1a2e',
    borderRadius: 15,
    borderWidth: 2,
    borderColor: '#4cc9f0',
    overflow: 'hidden',
  },
  dropdownTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#4cc9f0',
    padding: 20,
    textAlign: 'center',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(76,201,240,0.3)',
    backgroundColor: 'rgba(0,0,0,0.2)',
  },
  dropdownScroll: {
    maxHeight: 300,
  },
  dropdownItem: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  dropdownItemSelected: {
    backgroundColor: 'rgba(76,201,240,0.2)',
    borderLeftWidth: 4,
    borderLeftColor: '#4cc9f0',
  },
  dropdownItemText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '500',
  },
  dropdownItemTextSelected: {
    color: '#4cc9f0',
    fontWeight: 'bold',
  },
  dropdownCloseButton: {
    padding: 15,
    backgroundColor: '#4cc9f0',
    alignItems: 'center',
  },
  dropdownCloseText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalContent: {
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 25,
    width: '90%',
    maxWidth: 400,
    borderWidth: 2,
    borderColor: '#4cc9f0',
  },
  modalClose: {
    alignSelf: 'flex-end',
    padding: 5,
  },
  modalCloseText: {
    color: '#8b8b9d',
    fontSize: 18,
    fontWeight: 'bold',
  },
  authTabs: {
    flexDirection: 'row',
    marginBottom: 20,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 10,
    padding: 4,
  },
  authTab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
  },
  authTabActive: {
    backgroundColor: '#4cc9f0',
  },
  authTabText: {
    color: '#8b8b9d',
    fontWeight: '500',
  },
  authTabTextActive: {
    color: '#fff',
    fontWeight: 'bold',
  },
  authForm: {
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#e0e0e0',
    marginBottom: 8,
    textAlign: 'center',
  },
  modalSubtitle: {
    color: '#8b8b9d',
    marginBottom: 25,
    textAlign: 'center',
    fontSize: 14,
  },
  btnModal: {
    backgroundColor: '#4cc9f0',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    width: '100%',
    marginTop: 10,
    marginBottom: 20,
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
    fontWeight: '500',
  },
  // Results Screen Styles
  resultsContainer: {
    flex: 1,
    backgroundColor: '#0a0f1f',
  },
  resultsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  backButton: {
    padding: 8,
  },
  backButtonText: {
    color: '#4cc9f0',
    fontSize: 16,
    fontWeight: '500',
  },
  resultsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#e0e0e0',
    textAlign: 'center',
  },
  resultsContent: {
    flex: 1,
    padding: 20,
  },
  mainScoreCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 20,
    padding: 25,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  scoreCircle: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  mainScore: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#4cc9f0',
  },
  scoreLabel: {
    color: '#8b8b9d',
    fontSize: 14,
    marginTop: 5,
  },
  profileInfo: {
    alignItems: 'flex-end',
  },
  profileTitle: {
    color: '#8b8b9d',
    fontSize: 14,
    marginBottom: 5,
  },
  profileValue: {
    color: '#e0e0e0',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  scoreBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  scoreBadgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  specsCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 20,
    padding: 25,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  sectionTitle: {
    color: '#e0e0e0',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  specsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  specItem: {
    width: '48%',
    marginBottom: 15,
  },
  specLabel: {
    color: '#8b8b9d',
    fontSize: 12,
    marginBottom: 5,
  },
  specValue: {
    color: '#e0e0e0',
    fontSize: 14,
    fontWeight: '500',
  },
    scoresCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 20,
    padding: 25,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  scoresList: {
    gap: 15,
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 30,
  },
  scoreCategory: {
    color: '#e0e0e0',
    fontSize: 14,
    fontWeight: '500',
    width: 100,
  },
  scoreBarContainer: {
    flex: 1,
    height: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 6,
    marginHorizontal: 15,
    overflow: 'hidden',
  },
  scoreBar: {
    height: '100%',
    borderRadius: 6,
  },
  scoreValue: {
    fontSize: 14,
    fontWeight: 'bold',
    width: 30,
    textAlign: 'right',
  },
  recommendationsCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 20,
    padding: 25,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  recommendationsList: {
    gap: 15,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  recommendationIcon: {
    fontSize: 16,
  },
  recommendationText: {
    color: '#e0e0e0',
    fontSize: 14,
    flex: 1,
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