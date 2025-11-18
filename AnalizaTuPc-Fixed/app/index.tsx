import { View, Text } from 'react-native';
import { Link } from 'expo-router';

export default function Home() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Home Screen</Text>
      <Link href="/explore">Ir a Explorar</Link>
      <Link href="/two">Ir a Two</Link>
      <Link href="/modal">Abrir Modal</Link>
    </View>
  );
}