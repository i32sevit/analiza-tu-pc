import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  Dimensions,
  Animated,
  Easing,
  TextInput,
  Modal
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const { width: screenWidth } = Dimensions.get('window');

// Colores IDÉNTICOS a tu web
const COLORS = {
  primary: '#4cc9f0',
  primaryDark: '#3a86f8',
  secondary: '#3a0ca3',
  accent: '#7209b7',
  success: '#00f5d4',
  warning: '#f72585',
  dark1: '#0a0f1f',
  dark2: '#1a1a2e',
  dark3: '#16213e',
  light: '#e0e0e0',
  gray: '#8b8b9d',
  glass: 'rgba(255, 255, 255, 0.05)',
  glassBorder: 'rgba(255, 255, 255, 0.1)'
};

const API_URL = 'https://analizatupc-backend.onrender.com';

export default function HomeScreen() {
  const [analisis, setAnalisis] = useState<any>(null);
  const [cargando, setCargando] = useState(false);
  const [progreso, setProgreso] = useState(0);
  const [pestañaActiva, setPestañaActiva] = useState('auto');
  const [modalVisible, setModalVisible] = useState(false);
  const [componenteSeleccionado, setComponenteSeleccionado] = useState<any>(null);

  const [datosManuales, setDatosManuales] = useState({
    cpuModel: '',
    cpuSpeed: '',
    cpuCores: '',
    ram: '',
    storageType: 'SSD',
    gpuModel: '',
    gpuVram: ''
  });

  // Animaciones
  const fadeAnim = useState(new Animated.Value(0))[0];
  const slideAnim = useState(new Animated.Value(50))[0];

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 800,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      })
    ]).start();
  }, []);

 const ejecutarAnalisis = async (esManual = false) => {
  setCargando(true);
  setProgreso(0);
  
  let interval: NodeJS.Timeout | null = null;
  
  try {
    interval = setInterval(() => {
      setProgreso(prev => {
        if (prev >= 90) {
          if (interval) clearInterval(interval);
          return 90;
        }
        return prev + 10;
      });
    }, 300);

    let datosAnalisis: any;
    
    if (esManual) {
      if (!datosManuales.cpuModel || !datosManuales.ram) {
        Alert.alert('Error', 'Por favor completa todos los campos requeridos');
        if (interval) clearInterval(interval);
        setCargando(false);
        return;
      }
      datosAnalisis = datosManuales;
    } else {
      datosAnalisis = {
        cpuModel: "Intel Core i7-10700K",
        cpuSpeed: "3.8",
        cpuCores: "8",
        ram: "16",
        storageType: "SSD",
        gpuModel: "NVIDIA GeForce RTX 3060", 
        gpuVram: "12"
      };
    }

    // LLAMADA REAL A TU API EN RENDER
    console.log('Enviando datos a:', API_URL);
    const response = await axios.post(`${API_URL}/api/analyze`, datosAnalisis, {
      timeout: 10000
    });
    
    if (interval) clearInterval(interval);
    setProgreso(100);
    setAnalisis(response.data);
    
    Alert.alert('✅ Análisis Completado', 'Datos recibidos desde tu servidor Render');
    
  } catch (error: any) {
    console.error('Error conectando con Render:', error);
    if (interval) clearInterval(interval);
    
    // Fallback a análisis local
    const datosFallback = esManual ? datosManuales : {
      cpuModel: "Intel Core i7-10700K",
      cpuSpeed: "3.8",
      cpuCores: "8",
      ram: "16",
      storageType: "SSD",
      gpuModel: "NVIDIA GeForce RTX 3060",
      gpuVram: "12"
    };
    
    const resultadoLocal = generarAnalisisLocal(datosFallback);
    setAnalisis(resultadoLocal);
    Alert.alert('⚠️ Análisis Local', 'No se pudo conectar con el servidor. Usando análisis local.');
  } finally {
    setCargando(false);
    setProgreso(0);
  }
};

  const generarAnalisisLocal = (datos: any) => {
    let puntuacionBase = 50;
    
    if (datos.cpuModel.includes('i9') || datos.cpuModel.includes('Ryzen 9')) puntuacionBase += 30;
    else if (datos.cpuModel.includes('i7') || datos.cpuModel.includes('Ryzen 7')) puntuacionBase += 20;
    else if (datos.cpuModel.includes('i5') || datos.cpuModel.includes('Ryzen 5')) puntuacionBase += 10;
    
    if (parseInt(datos.ram) >= 32) puntuacionBase += 20;
    else if (parseInt(datos.ram) >= 16) puntuacionBase += 15;
    else if (parseInt(datos.ram) >= 8) puntuacionBase += 10;
    
    if (datos.storageType === 'NVMe') puntuacionBase += 15;
    else if (datos.storageType === 'SSD') puntuacionBase += 10;
    
    if (datos.gpuModel.includes('RTX 40') || datos.gpuModel.includes('RX 7900')) puntuacionBase += 25;
    else if (datos.gpuModel.includes('RTX 30') || datos.gpuModel.includes('RX 6000')) puntuacionBase += 20;
    
    puntuacionBase = Math.min(puntuacionBase, 100);

    return {
      main_profile: puntuacionBase >= 70 ? 'Gaming/Profesional' : puntuacionBase >= 50 ? 'Multimedia' : 'Básico',
      main_score: puntuacionBase,
      scores: {
        'Gaming': Math.min(puntuacionBase + 5, 100),
        'Diseño': Math.min(puntuacionBase + 3, 100),
        'Oficina': Math.min(puntuacionBase + 10, 100),
        'Desarrollo': Math.min(puntuacionBase + 2, 100),
        'Streaming': Math.min(puntuacionBase - 5, 100)
      },
      componentes: {
        cpu: {
          nombre: datos.cpuModel,
          puntuacion: Math.min(puntuacionBase + 10, 100),
          detalles: `${datos.cpuSpeed} GHz, ${datos.cpuCores} núcleos`
        },
        ram: {
          nombre: 'Memoria RAM',
          puntuacion: Math.min(puntuacionBase + 5, 100),
          detalles: `${datos.ram} GB`
        },
        almacenamiento: {
          nombre: 'Almacenamiento',
          puntuacion: Math.min(puntuacionBase + 8, 100),
          detalles: datos.storageType
        },
        gpu: {
          nombre: datos.gpuModel,
          puntuacion: Math.min(puntuacionBase + 12, 100),
          detalles: `${datos.gpuVram} GB VRAM`
        }
      },
      recomendaciones: [
        'Mantén tus controladores actualizados para el mejor rendimiento',
        'Realiza mantenimiento regular del sistema',
        'Considera optimizaciones de software para maximizar el rendimiento'
      ]
    };
  };

  const obtenerColorPuntuacion = (score: number) => {
    if (score >= 80) return COLORS.success;
    if (score >= 60) return COLORS.primary;
    if (score >= 40) return COLORS.warning;
    return COLORS.accent;
  };

  const obtenerEstrellas = (score: number) => {
    const estrellasLlenas = Math.floor((score / 100) * 5);
    const estrellas = [];
    
    for (let i = 0; i < 5; i++) {
      estrellas.push(
        <Ionicons
          key={i}
          name={i < estrellasLlenas ? "star" : "star-outline"}
          size={16}
          color={COLORS.warning}
        />
      );
    }
    return estrellas;
  };

  const renderHeader = () => (
    <Animated.View 
      style={[
        styles.header,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }]
        }
      ]}
    >
      <View style={styles.logoContainer}>
        <View style={styles.logo}>
          <Ionicons name="desktop" size={40} color={COLORS.primary} />
        </View>
      </View>
      <Text style={styles.title}>AnalizaTuPc</Text>
      <Text style={styles.subtitle}>
        Análisis profesional de hardware para determinar el rendimiento de tu equipo
      </Text>
    </Animated.View>
  );

  const renderTabs = () => (
    <View style={styles.tabsContainer}>
      <TouchableOpacity
        style={[styles.tab, pestañaActiva === 'auto' && styles.tabActive]}
        onPress={() => setPestañaActiva('auto')}
      >
        <Text style={[styles.tabText, pestañaActiva === 'auto' && styles.tabTextActive]}>
          Automático
        </Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.tab, pestañaActiva === 'manual' && styles.tabActive]}
        onPress={() => setPestañaActiva('manual')}
      >
        <Text style={[styles.tabText, pestañaActiva === 'manual' && styles.tabTextActive]}>
          Manual
        </Text>
      </TouchableOpacity>
    </View>
  );

  const renderAnalisisAutomatico = () => (
    <View style={styles.tabContent}>
      <TouchableOpacity
        style={[styles.btn, cargando && styles.btnDisabled]}
        onPress={() => ejecutarAnalisis(false)}
        disabled={cargando}
      >
        <LinearGradient
          colors={[COLORS.primary, COLORS.primaryDark]}
          style={styles.btnGradient}
        >
          <Ionicons name="search" size={24} color="white" />
          <Text style={styles.btnText}>
            {cargando ? 'Analizando...' : 'Iniciar Análisis Automático'}
          </Text>
        </LinearGradient>
      </TouchableOpacity>

      {cargando && (
        <View style={styles.progressContainer}>
          <View style={styles.progressHeader}>
            <Text style={styles.progressText}>Progreso del análisis</Text>
            <Text style={styles.progressText}>{progreso}%</Text>
          </View>
          <View style={styles.progressBar}>
            <View 
              style={[
                styles.progressFill,
                { width: `${progreso}%`, backgroundColor: COLORS.primary }
              ]} 
            />
          </View>
        </View>
      )}
    </View>
  );

  const renderEntradaManual = () => (
    <View style={styles.tabContent}>
      <ScrollView style={styles.formContainer} showsVerticalScrollIndicator={false}>
        <Text style={styles.formLabel}>Modelo de CPU</Text>
        <TextInput
          style={styles.input}
          placeholder="Ej: Intel Core i7-10700K"
          placeholderTextColor={COLORS.gray}
          value={datosManuales.cpuModel}
          onChangeText={(text) => setDatosManuales({...datosManuales, cpuModel: text})}
        />

        <View style={styles.row}>
          <View style={styles.col}>
            <Text style={styles.formLabel}>Velocidad (GHz)</Text>
            <TextInput
              style={styles.input}
              placeholder="3.8"
              placeholderTextColor={COLORS.gray}
              keyboardType="numeric"
              value={datosManuales.cpuSpeed}
              onChangeText={(text) => setDatosManuales({...datosManuales, cpuSpeed: text})}
            />
          </View>
          <View style={styles.col}>
            <Text style={styles.formLabel}>Núcleos</Text>
            <TextInput
              style={styles.input}
              placeholder="8"
              placeholderTextColor={COLORS.gray}
              keyboardType="numeric"
              value={datosManuales.cpuCores}
              onChangeText={(text) => setDatosManuales({...datosManuales, cpuCores: text})}
            />
          </View>
        </View>

        <Text style={styles.formLabel}>Memoria RAM (GB)</Text>
        <TextInput
          style={styles.input}
          placeholder="16"
          placeholderTextColor={COLORS.gray}
          keyboardType="numeric"
          value={datosManuales.ram}
          onChangeText={(text) => setDatosManuales({...datosManuales, ram: text})}
        />

        <Text style={styles.formLabel}>Tipo de Almacenamiento</Text>
        <View style={styles.radioContainer}>
          {['SSD', 'HDD', 'NVMe'].map((tipo) => (
            <TouchableOpacity
              key={tipo}
              style={styles.radioOption}
              onPress={() => setDatosManuales({...datosManuales, storageType: tipo})}
            >
              <View style={styles.radioCircle}>
                {datosManuales.storageType === tipo && <View style={styles.radioSelected} />}
              </View>
              <Text style={styles.radioText}>{tipo}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={styles.formLabel}>Modelo de GPU</Text>
        <TextInput
          style={styles.input}
          placeholder="Ej: NVIDIA GeForce RTX 3060"
          placeholderTextColor={COLORS.gray}
          value={datosManuales.gpuModel}
          onChangeText={(text) => setDatosManuales({...datosManuales, gpuModel: text})}
        />

        <Text style={styles.formLabel}>VRAM de GPU (GB)</Text>
        <TextInput
          style={styles.input}
          placeholder="12"
          placeholderTextColor={COLORS.gray}
          keyboardType="numeric"
          value={datosManuales.gpuVram}
          onChangeText={(text) => setDatosManuales({...datosManuales, gpuVram: text})}
        />
      </ScrollView>

      <TouchableOpacity
        style={styles.btn}
        onPress={() => ejecutarAnalisis(true)}
      >
        <LinearGradient
          colors={[COLORS.primary, COLORS.primaryDark]}
          style={styles.btnGradient}
        >
          <Ionicons name="analytics" size={24} color="white" />
          <Text style={styles.btnText}>Analizar con Datos Manuales</Text>
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );

  const renderResultados = () => {
    if (!analisis) return null;

    return (
      <Animated.View 
        style={[
          styles.resultsContainer,
          {
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }]
          }
        ]}
      >
        <LinearGradient
          colors={[COLORS.primary + '20', COLORS.success + '20']}
          style={styles.resultsHeader}
        >
          <Text style={styles.resultsTitle}>Resultados del Análisis</Text>
          <Text style={styles.resultsSubtitle}>Evaluación completa del rendimiento de tu sistema</Text>
        </LinearGradient>

        <View style={styles.scoreDisplay}>
          <View style={styles.scoreCircle}>
            <View style={[styles.scoreProgress, { 
              borderColor: obtenerColorPuntuacion(analisis.main_score)
            }]} />
            <View style={styles.scoreValueContainer}>
              <Text style={styles.scoreValue}>{analisis.main_score}%</Text>
              <Text style={styles.scoreLabel}>{analisis.main_profile}</Text>
            </View>
          </View>
        </View>

        <View style={styles.profileGrid}>
          {Object.entries(analisis.scores).map(([perfil, puntuacion]) => {
            const puntuacionNum = Number(puntuacion);
            return (
              <TouchableOpacity
                key={perfil}
                style={styles.profileCard}
                onPress={() => {
                  setComponenteSeleccionado({ 
                    tipo: 'perfil', 
                    nombre: perfil, 
                    puntuacion: puntuacionNum 
                  } as any);
                  setModalVisible(true);
                }}
              >
                <Text style={styles.profileName}>{perfil}</Text>
                <Text style={[styles.profileScore, { color: obtenerColorPuntuacion(puntuacionNum) }]}>
                  {puntuacionNum}%
                </Text>
                <View style={styles.profileBar}>
                  <View 
                    style={[
                      styles.profileFill,
                      { width: `${puntuacionNum}%`, backgroundColor: obtenerColorPuntuacion(puntuacionNum) }
                    ]} 
                  />
                </View>
                <View style={styles.ratingStars}>
                  {obtenerEstrellas(puntuacionNum)}
                </View>
              </TouchableOpacity>
            );
          })}
        </View>

        <View style={styles.componentAnalysis}>
          <Text style={styles.sectionTitle}>Análisis por Componente</Text>
          <View style={styles.componentGrid}>
            {Object.entries(analisis.componentes).map(([tipo, componente]) => {
              const comp = componente as any;
              return (
                <TouchableOpacity
                  key={tipo}
                  style={styles.componentCard}
                  onPress={() => {
                    setComponenteSeleccionado({ tipo, ...comp } as any);
                    setModalVisible(true);
                  }}
                >
                  <View style={styles.componentHeader}>
                    <View style={styles.componentIcon}>
                      <Ionicons 
                        name={
                          tipo === 'cpu' ? 'hardware-chip' :
                          tipo === 'ram' ? 'layers' :
                          tipo === 'almacenamiento' ? 'save' : 'game-controller'
                        } 
                        size={24} 
                        color={COLORS.primary} 
                      />
                    </View>
                    <Text style={styles.componentName}>{comp.nombre}</Text>
                  </View>
                  <Text style={styles.componentDetails}>{comp.detalles}</Text>
                  <View style={styles.componentRating}>
                    <View style={styles.ratingStars}>
                      {obtenerEstrellas(comp.puntuacion)}
                    </View>
                    <Text style={styles.ratingText}>{comp.puntuacion}%</Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        <View style={styles.recommendations}>
          <Text style={styles.recommendationsTitle}>
            <Ionicons name="bulb" size={24} color={COLORS.success} />
            Recomendaciones de Mejora
          </Text>
          <View style={styles.recommendationsList}>
            {analisis.recomendaciones.map((recomendacion: string, index: number) => (
              <View key={index} style={styles.recommendationItem}>
                <Ionicons name="checkmark-circle" size={20} color={COLORS.success} />
                <Text style={styles.recommendationText}>{recomendacion}</Text>
              </View>
            ))}
          </View>
        </View>
      </Animated.View>
    );
  };

  const renderModalDetalles = () => (
    <Modal
      animationType="slide"
      transparent={true}
      visible={modalVisible}
      onRequestClose={() => setModalVisible(false)}
    >
      <View style={styles.modalContainer}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>
              {componenteSeleccionado?.nombre}
            </Text>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setModalVisible(false)}
            >
              <Ionicons name="close" size={24} color={COLORS.light} />
            </TouchableOpacity>
          </View>
          
          {componenteSeleccionado && (
            <ScrollView style={styles.modalBody}>
              <View style={styles.modalScore}>
                <Text style={styles.modalScoreValue}>
                  {componenteSeleccionado.puntuacion}%
                </Text>
                <Text style={styles.modalScoreLabel}>Puntuación</Text>
              </View>
              
              {componenteSeleccionado.detalles && (
                <View style={styles.modalSection}>
                  <Text style={styles.modalSectionTitle}>Detalles</Text>
                  <Text style={styles.modalSectionText}>
                    {componenteSeleccionado.detalles}
                  </Text>
                </View>
              )}
              
              <View style={styles.modalSection}>
                <Text style={styles.modalSectionTitle}>Evaluación</Text>
                <View style={styles.ratingStars}>
                  {obtenerEstrellas(componenteSeleccionado.puntuacion)}
                </View>
                <Text style={styles.modalEvaluation}>
                  {componenteSeleccionado.puntuacion >= 80 ? 'Excelente' :
                   componenteSeleccionado.puntuacion >= 60 ? 'Bueno' :
                   componenteSeleccionado.puntuacion >= 40 ? 'Aceptable' : 'Necesita mejora'}
                </Text>
              </View>
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );

  return (
    <LinearGradient
      colors={[COLORS.dark1, COLORS.dark2, COLORS.dark3]}
      style={styles.container}
    >
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {renderHeader()}
        
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.cardIcon}>
              <Ionicons name="rocket" size={28} color={COLORS.primary} />
            </View>
            <Text style={styles.cardTitle}>Análisis del Sistema</Text>
          </View>
          
          {renderTabs()}
          
          {pestañaActiva === 'auto' ? renderAnalisisAutomatico() : renderEntradaManual()}
        </View>

        {renderResultados()}
        
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            AnalizaTuPc &copy; 2025 - Herramienta profesional de análisis de hardware
          </Text>
        </View>
      </ScrollView>

      {renderModalDetalles()}
    </LinearGradient>
  );
}

// ESTILOS (igual que antes)
const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    paddingVertical: 40,
    paddingHorizontal: 20,
    borderBottomWidth: 3,
    borderBottomColor: 'rgba(76, 201, 240, 0.3)',
    marginBottom: 30,
  },
  logoContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 100,
    height: 100,
    backgroundColor: 'rgba(76, 201, 240, 0.1)',
    borderRadius: 25,
    marginBottom: 20,
    overflow: 'hidden',
  },
  logo: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginBottom: 10,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.gray,
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: 20,
  },
  card: {
    backgroundColor: COLORS.glass,
    borderRadius: 20,
    padding: 25,
    marginHorizontal: 20,
    marginBottom: 30,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 25,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.glassBorder,
  },
  cardIcon: {
    width: 60,
    height: 60,
    backgroundColor: 'rgba(76, 201, 240, 0.1)',
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 15,
  },
  cardTitle: {
    fontSize: 24,
    fontWeight: '600',
    color: COLORS.light,
  },
  tabsContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    borderRadius: 12,
    padding: 5,
    marginBottom: 25,
  },
  tab: {
    flex: 1,
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  tabActive: {
    backgroundColor: 'rgba(76, 201, 240, 0.2)',
  },
  tabText: {
    color: COLORS.gray,
    fontWeight: '500',
    fontSize: 14,
  },
  tabTextActive: {
    color: COLORS.primary,
  },
  tabContent: {
    minHeight: 200,
  },
  btn: {
    borderRadius: 14,
    overflow: 'hidden',
    marginBottom: 20,
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
    elevation: 8,
  },
  btnGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    gap: 12,
  },
  btnText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 18,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  progressContainer: {
    marginVertical: 25,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  progressText: {
    color: COLORS.gray,
    fontSize: 14,
  },
  progressBar: {
    height: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  formContainer: {
    maxHeight: 400,
    marginBottom: 20,
  },
  formLabel: {
    color: COLORS.light,
    fontWeight: '500',
    marginBottom: 8,
    fontSize: 16,
  },
  input: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
    borderRadius: 10,
    padding: 15,
    color: COLORS.light,
    fontSize: 16,
    marginBottom: 20,
  },
  row: {
    flexDirection: 'row',
    gap: 15,
  },
  col: {
    flex: 1,
  },
  radioContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 10,
  },
  radioCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  radioSelected: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.primary,
  },
  radioText: {
    color: COLORS.light,
    fontSize: 14,
  },
  resultsContainer: {
    backgroundColor: COLORS.glass,
    borderRadius: 20,
    padding: 25,
    marginHorizontal: 20,
    marginBottom: 30,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
  },
  resultsHeader: {
    borderRadius: 16,
    padding: 25,
    marginBottom: 25,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
  },
  resultsTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 10,
  },
  resultsSubtitle: {
    color: COLORS.gray,
    textAlign: 'center',
    fontSize: 16,
  },
  scoreDisplay: {
    alignItems: 'center',
    marginVertical: 30,
  },
  scoreCircle: {
    width: 200,
    height: 200,
    borderRadius: 100,
    borderWidth: 10,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  scoreProgress: {
    position: 'absolute',
    width: 200,
    height: 200,
    borderRadius: 100,
    borderWidth: 10,
    borderLeftColor: 'transparent',
    borderBottomColor: 'transparent',
    borderRightColor: 'transparent',
  },
  scoreValueContainer: {
    alignItems: 'center',
  },
  scoreValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.light,
  },
  scoreLabel: {
    color: COLORS.gray,
    fontSize: 16,
    marginTop: 5,
  },
  profileGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 15,
    marginBottom: 25,
  },
  profileCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
    alignItems: 'center',
  },
  profileName: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.light,
    marginBottom: 10,
    textAlign: 'center',
  },
  profileScore: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  profileBar: {
    width: '100%',
    height: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 10,
  },
  profileFill: {
    height: '100%',
    borderRadius: 4,
  },
  ratingStars: {
    flexDirection: 'row',
  },
  componentAnalysis: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: COLORS.light,
    textAlign: 'center',
    marginBottom: 20,
  },
  componentGrid: {
    gap: 15,
  },
  componentCard: {
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
  },
  componentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  componentIcon: {
    width: 50,
    height: 50,
    backgroundColor: 'rgba(76, 201, 240, 0.1)',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 15,
  },
  componentName: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.light,
    flex: 1,
  },
  componentDetails: {
    color: COLORS.gray,
    fontSize: 14,
    marginBottom: 15,
  },
  componentRating: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  ratingText: {
    color: COLORS.gray,
    fontSize: 14,
  },
  recommendations: {
    backgroundColor: 'rgba(0, 245, 212, 0.1)',
    borderRadius: 16,
    padding: 25,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
  },
  recommendationsTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: COLORS.light,
    marginBottom: 15,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  recommendationsList: {
    gap: 10,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  recommendationText: {
    color: COLORS.light,
    fontSize: 14,
    flex: 1,
    lineHeight: 20,
  },
  footer: {
    padding: 30,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: COLORS.glassBorder,
  },
  footerText: {
    color: COLORS.gray,
    fontSize: 14,
    textAlign: 'center',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
  },
  modalContent: {
    backgroundColor: COLORS.dark2,
    borderRadius: 20,
    padding: 25,
    margin: 20,
    borderWidth: 1,
    borderColor: COLORS.glassBorder,
    maxHeight: '80%',
    width: '90%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.glassBorder,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.light,
    flex: 1,
  },
  closeButton: {
    padding: 5,
  },
  modalBody: {
    flex: 1,
  },
  modalScore: {
    alignItems: 'center',
    marginVertical: 20,
  },
  modalScoreValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: COLORS.primary,
  },
  modalScoreLabel: {
    color: COLORS.gray,
    fontSize: 16,
    marginTop: 5,
  },
  modalSection: {
    marginBottom: 25,
  },
  modalSectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.light,
    marginBottom: 10,
  },
  modalSectionText: {
    color: COLORS.gray,
    fontSize: 16,
    lineHeight: 22,
  },
  modalEvaluation: {
    color: COLORS.success,
    fontSize: 16,
    fontWeight: '600',
    marginTop: 10,
  },
});