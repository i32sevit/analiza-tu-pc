import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0a0f1f',
          borderTopColor: 'rgba(76, 201, 240, 0.2)',
        },
        tabBarActiveTintColor: '#4cc9f0',
        tabBarInactiveTintColor: '#8b8b9d',
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Analizar',
          tabBarIcon: ({ size, color }) => (
            <Ionicons name="analytics" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}