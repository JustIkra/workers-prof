<template>
  <div class="landing-page">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <div class="logo-large">
          <span class="logo-icon">ЦМ</span>
        </div>
        <h1 class="hero-title">Цифровая модель управления компетенциями</h1>
        <p class="hero-subtitle">
          Профессиональная система оценки пригодности и развития персонала
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="router.push('/login')">
            Войти в систему
          </el-button>
          <el-button size="large" @click="router.push('/register')">
            Зарегистрироваться
          </el-button>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="features">
      <div class="container">
        <h2 class="section-title">Возможности системы</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="40"><Document /></el-icon>
            </div>
            <h3>Автоматическая обработка отчётов</h3>
            <p>
              Загрузите отчёты в формате DOCX. Система автоматически извлечёт метрики
              с использованием OCR и AI технологий.
            </p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="40"><DataAnalysis /></el-icon>
            </div>
            <h3>Расчёт профессиональной пригодности</h3>
            <p>
              Получайте объективную оценку соответствия сотрудников требованиям
              различных профессиональных областей.
            </p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="40"><TrendCharts /></el-icon>
            </div>
            <h3>Персонализированные рекомендации</h3>
            <p>
              Система формирует индивидуальные рекомендации по развитию на основе
              выявленных сильных сторон и зон роста.
            </p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="40"><User /></el-icon>
            </div>
            <h3>Управление участниками</h3>
            <p>
              Единый реестр участников с полной историей оценок, отчётов и
              результатов анализа компетенций.
            </p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="40"><SetUp /></el-icon>
            </div>
            <h3>Гибкие весовые коэффициенты</h3>
            <p>
              Настраивайте весовые таблицы для различных профессиональных областей.
              Поддержка версионирования и аудита изменений.
            </p>
          </div>

          <div class="feature-card">
            <div class="feature-icon">
              <el-icon :size="40"><Finished /></el-icon>
            </div>
            <h3>Итоговые отчёты</h3>
            <p>
              Формируйте комплексные отчёты с результатами оценки, рекомендациями
              и планами развития в удобном формате.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Process Section -->
    <section class="process">
      <div class="container">
        <h2 class="section-title">Как это работает</h2>
        <div class="process-steps">
          <div class="process-step">
            <div class="step-number">1</div>
            <h3>Загрузка данных</h3>
            <p>Загрузите отчёты участников в систему</p>
          </div>
          <div class="process-arrow">→</div>
          <div class="process-step">
            <div class="step-number">2</div>
            <h3>Извлечение метрик</h3>
            <p>Автоматическое распознавание показателей</p>
          </div>
          <div class="process-arrow">→</div>
          <div class="process-step">
            <div class="step-number">3</div>
            <h3>Расчёт оценки</h3>
            <p>Вычисление профессиональной пригодности</p>
          </div>
          <div class="process-arrow">→</div>
          <div class="process-step">
            <div class="step-number">4</div>
            <h3>Рекомендации</h3>
            <p>Получение персонализированных советов</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Benefits Section -->
    <section class="benefits">
      <div class="container">
        <h2 class="section-title">Преимущества</h2>
        <div class="benefits-grid">
          <div class="benefit-item">
            <el-icon :size="24" color="#00798D"><CircleCheck /></el-icon>
            <span>Автоматизация оценки персонала</span>
          </div>
          <div class="benefit-item">
            <el-icon :size="24" color="#00798D"><CircleCheck /></el-icon>
            <span>Объективность и прозрачность критериев</span>
          </div>
          <div class="benefit-item">
            <el-icon :size="24" color="#00798D"><CircleCheck /></el-icon>
            <span>Сокращение времени на обработку данных</span>
          </div>
          <div class="benefit-item">
            <el-icon :size="24" color="#00798D"><CircleCheck /></el-icon>
            <span>Централизованное хранение информации</span>
          </div>
          <div class="benefit-item">
            <el-icon :size="24" color="#00798D"><CircleCheck /></el-icon>
            <span>Поддержка нескольких типов отчётов</span>
          </div>
          <div class="benefit-item">
            <el-icon :size="24" color="#00798D"><CircleCheck /></el-icon>
            <span>Версионирование весовых коэффициентов</span>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="cta">
      <div class="cta-content">
        <h2>Готовы начать?</h2>
        <p>Зарегистрируйтесь в системе и получите доступ к функционалу оценки компетенций</p>
        <div class="cta-actions">
          <el-button type="primary" size="large" @click="router.push('/register')">
            Зарегистрироваться
          </el-button>
          <el-button size="large" @click="router.push('/login')">
            Войти
          </el-button>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-brand">
            <div class="logo">
              <span class="logo-icon-small">ЦМ</span>
              <span class="logo-text">Цифровая модель УК</span>
            </div>
            <p class="footer-description">
              Система профессиональной оценки и развития персонала
            </p>
          </div>
          <div class="footer-info">
            <p>&copy; 2025 Цифровая модель управления компетенциями</p>
            <p>Версия 1.0</p>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import {
  Document,
  DataAnalysis,
  TrendCharts,
  User,
  SetUp,
  Finished,
  CircleCheck
} from '@element-plus/icons-vue'

const router = useRouter()
</script>

<style scoped>
.landing-page {
  background-color: #fff;
}

/* Hero Section */
.hero {
  background: linear-gradient(135deg, #00798D 0%, #025E6D 100%);
  color: white;
  padding: 100px 20px;
  text-align: center;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
}

.logo-large {
  margin-bottom: 30px;
}

.logo-icon {
  width: 80px;
  height: 80px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 32px;
  backdrop-filter: blur(10px);
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  margin: 0 0 20px 0;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 20px;
  margin: 0 0 40px 0;
  opacity: 0.95;
  line-height: 1.5;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* Features Section */
.features {
  padding: 80px 20px;
  background-color: #f5f7fa;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

.section-title {
  font-size: 36px;
  font-weight: 700;
  text-align: center;
  margin: 0 0 60px 0;
  color: #303133;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 30px;
}

.feature-card {
  background: white;
  padding: 40px 30px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s, box-shadow 0.3s;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.feature-icon {
  color: var(--color-primary);
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 15px 0;
  color: #303133;
}

.feature-card p {
  font-size: 15px;
  line-height: 1.6;
  color: #606266;
  margin: 0;
}

/* Process Section */
.process {
  padding: 80px 20px;
  background-color: white;
}

.process-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 20px;
}

.process-step {
  text-align: center;
  max-width: 200px;
}

.step-number {
  width: 60px;
  height: 60px;
  background-color: var(--color-primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  margin: 0 auto 20px auto;
}

.process-step h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 10px 0;
  color: #303133;
}

.process-step p {
  font-size: 14px;
  color: #606266;
  margin: 0;
}

.process-arrow {
  font-size: 32px;
  color: var(--color-primary);
  font-weight: 700;
}

/* Benefits Section */
.benefits {
  padding: 80px 20px;
  background-color: #f5f7fa;
}

.benefits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.benefit-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.benefit-item span {
  font-size: 15px;
  color: #303133;
}

/* CTA Section */
.cta {
  background: linear-gradient(135deg, #00798D 0%, #025E6D 100%);
  color: white;
  padding: 80px 20px;
  text-align: center;
}

.cta-content {
  max-width: 700px;
  margin: 0 auto;
}

.cta h2 {
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 16px 0;
}

.cta p {
  font-size: 18px;
  margin: 0 0 40px 0;
  opacity: 0.95;
}

.cta-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* Footer */
.footer {
  background-color: #1F2937;
  color: #E5E7EB;
  padding: 40px 20px;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 30px;
}

.footer-brand .logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.logo-icon-small {
  width: 32px;
  height: 32px;
  background-color: var(--color-primary);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #E5E7EB;
}

.footer-description {
  font-size: 14px;
  color: #9CA3AF;
  margin: 0;
}

.footer-info {
  text-align: right;
}

.footer-info p {
  margin: 4px 0;
  font-size: 14px;
  color: #9CA3AF;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-title {
    font-size: 32px;
  }

  .hero-subtitle {
    font-size: 18px;
  }

  .section-title {
    font-size: 28px;
  }

  .process-steps {
    flex-direction: column;
  }

  .process-arrow {
    transform: rotate(90deg);
  }

  .footer-content {
    flex-direction: column;
    text-align: center;
  }

  .footer-info {
    text-align: center;
  }
}
</style>
