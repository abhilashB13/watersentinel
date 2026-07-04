/**
 * Module: App.tsx
 * Purpose: Root component. Bottom tab navigation with 4 screens.
 *          Manages report result state passed between Report → Result screens.
 * Component: App Root
 */

import React, { useState } from 'react';
import { StatusBar, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import ReportScreen from './src/screens/ReportScreen';
import ResultScreen from './src/screens/ResultScreen';
import MapScreen from './src/screens/MapScreen';
import AboutScreen from './src/screens/AboutScreen';
import { WaterReportResponse } from './src/api/watersentinel';

const Tab = createBottomTabNavigator();
const ReportStack = createNativeStackNavigator();

// ── Report Stack Navigator ─────────────────────────────────────────────────────
// Report screen → Result screen when submission completes

function ReportNavigator({
  onViewMap,
}: {
  onViewMap: () => void;
}) {
  const [reportResult, setReportResult] = useState<WaterReportResponse | null>(null);

  if (reportResult) {
    return (
      <ResultScreen
        result={reportResult}
        onNewReport={() => setReportResult(null)}
        onViewMap={() => {
          setReportResult(null);
          onViewMap();
        }}
      />
    );
  }

  return (
    <ReportScreen
      onReportComplete={(result) => setReportResult(result)}
    />
  );
}

// ── Tab Navigator ──────────────────────────────────────────────────────────────

export default function App() {
  const [activeTab, setActiveTab] = useState('Report');

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor="#1565C0" />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            headerShown: false,
            tabBarActiveTintColor: '#1565C0',
            tabBarInactiveTintColor: '#9E9E9E',
            tabBarStyle: {
              backgroundColor: '#fff',
              borderTopWidth: 1,
              borderTopColor: '#E0E0E0',
              paddingBottom: 4,
              height: 58,
            },
            tabBarLabelStyle: {
              fontSize: 11,
              fontWeight: '500',
            },
            tabBarIcon: ({ focused, color, size }) => {
              let iconName: keyof typeof Ionicons.glyphMap = 'water';
              if (route.name === 'Report') {
                iconName = focused ? 'add-circle' : 'add-circle-outline';
              } else if (route.name === 'Map') {
                iconName = focused ? 'map' : 'map-outline';
              } else if (route.name === 'About') {
                iconName = focused ? 'information-circle' : 'information-circle-outline';
              }
              return <Ionicons name={iconName} size={size} color={color} />;
            },
          })}
        >
          <Tab.Screen
            name="Report"
            options={{ tabBarLabel: 'Report' }}
          >
            {() => (
              <ReportNavigator
                onViewMap={() => {}}
              />
            )}
          </Tab.Screen>

          <Tab.Screen
            name="Map"
            component={MapScreen}
            options={{ tabBarLabel: 'Community Map' }}
          />

          <Tab.Screen
            name="About"
            component={AboutScreen}
            options={{ tabBarLabel: 'About' }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
