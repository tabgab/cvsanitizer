#!/usr/bin/env python3
"""
PDF CV Generator for Testing

Creates international PDF CV files with challenging PII detection scenarios.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def register_custom_fonts():
    """Register custom fonts for international characters."""
    try:
        # Try to register Arial for better international support
        pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
        return True
    except:
        # Fallback to default fonts
        return False

def create_cv_pdf(filename, content_data, country_code):
    """Create a PDF CV with the given content."""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20
    )
    
    content = []
    
    # Title
    content.append(Paragraph(content_data['title'], title_style))
    content.append(Spacer(1, 20))
    
    # Personal Information
    content.append(Paragraph("Personal Information", heading_style))
    for key, value in content_data['personal'].items():
        content.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
    content.append(Spacer(1, 12))
    
    # Education
    content.append(Paragraph("Education", heading_style))
    for edu in content_data['education']:
        content.append(Paragraph(f"<b>{edu['degree']}</b> ({edu['years']})", styles['Normal']))
        content.append(Paragraph(f"{edu['institution']}", styles['Normal']))
        if 'details' in edu:
            content.append(Paragraph(f"{edu['details']}", styles['Normal']))
        content.append(Spacer(1, 6))
    
    # Experience
    content.append(Paragraph("Work Experience", heading_style))
    for exp in content_data['experience']:
        content.append(Paragraph(f"<b>{exp['position']}</b> at {exp['company']} ({exp['years']})", styles['Normal']))
        if 'responsibilities' in exp:
            for resp in exp['responsibilities']:
                content.append(Paragraph(f"• {resp}", styles['Normal']))
        content.append(Spacer(1, 6))
    
    # Skills
    content.append(Paragraph("Skills", heading_style))
    content.append(Paragraph(content_data['skills'], styles['Normal']))
    content.append(Spacer(1, 12))
    
    # Contact
    content.append(Paragraph("Contact", heading_style))
    for key, value in content_data['contact'].items():
        content.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
    
    # Build PDF
    doc.build(content)
    return True

def create_german_cv():
    """Create German CV with challenging PII."""
    content = {
        'title': 'Lebenslauf',
        'personal': {
            'Name': 'Dr. Hans-Peter Müller',
            'Geburtsdatum': '15.03.1985',
            'Alter': '38 Jahre',
            'Nationalität': 'Deutsch',
            'Adresse': 'Hauptstraße 42, 80331 München, Deutschland',
            'Telefon': '+49 89 12345678',
            'Mobil': '+49 160 98765432',
            'Email': 'hans.mueller@web.de',
            'LinkedIn': 'https://linkedin.com/in/hanspetermueller',
            'GitHub': 'https://github.com/hansmueller85'
        },
        'education': [
            {
                'degree': 'Doktor-Ingenieur (Dr.-Ing.)',
                'years': '2010-2014',
                'institution': 'Technische Universität München',
                'details': 'Fachrichtung: Informatik, Note: 1,3'
            },
            {
                'degree': 'Master of Science',
                'years': '2008-2010',
                'institution': 'Ludwig-Maximilians-Universität München',
                'details': 'Fachrichtung: Mathematik und Informatik'
            }
        ],
        'experience': [
            {
                'position': 'Senior Software Architect',
                'company': 'BMW Group',
                'years': '2018-Heute',
                'responsibilities': [
                    'Entwicklung von KI-Systemen für autonome Fahrzeuge',
                    'Leitung eines Teams von 15 Entwicklern',
                    'Architektur von Microservices'
                ]
            },
            {
                'position': 'Software Engineer',
                'company': 'SAP SE',
                'years': '2014-2018',
                'responsibilities': [
                    'Entwicklung von ERP-Systemen',
                    'Datenbankoptimierung',
                    'Agile Methoden'
                ]
            }
        ],
        'skills': 'Programmiersprachen: Python, Java, C++, Go | Cloud: AWS, Azure, GCP | Datenbanken: PostgreSQL, MongoDB, Redis',
        'contact': {
            'Website': 'https://hansmueller.de',
            'Twitter': '@hansmueller_tech',
            'Xing': 'https://xing.com/profile/hans_mueller'
        }
    }
    
    return create_cv_pdf('imaginary_test_cvs/CV_Hans_Mueller.pdf', content, 'DE')

def create_japanese_cv():
    """Create Japanese CV with challenging PII."""
    content = {
        'title': '履歴書',
        'personal': {
            'Name': '田中 太郎 (Tanaka Taro)',
            '生年月日': '1990年4月22日',
            '年齢': '33歳',
            '国籍': '日本',
            '住所': '東京都渋谷区神南1-2-3 ABCマンション101号',
            '電話': '+81 3-1234-5678',
            '携帯': '+81 90-1234-5678',
            'Email': 'tanaka.taro@gmail.com',
            'LinkedIn': 'https://linkedin.com/in/tanakataro',
            'GitHub': 'https://github.com/tanakataro90'
        },
        'education': [
            {
                'degree': '修士号 (Master of Engineering)',
                'years': '2012-2014',
                'institution': '東京大学大学院',
                'details': '情報理工学系研究科'
            },
            {
                'degree': '学士号 (Bachelor of Engineering)',
                'years': '2008-2012',
                'institution': '東京大学',
                'details': '工学部電子情報工学科'
            }
        ],
        'experience': [
            {
                'position': 'シニアソフトウェアエンジニア',
                'company': '株式会社ソニー',
                'years': '2019-現在',
                'responsibilities': [
                    'ゲームエンジンの開発',
                    'パフォーマンス最適化',
                    'チームリーダー'
                ]
            },
            {
                'position': 'ソフトウェアエンジニア',
                'company': '株式会社任天堂',
                'years': '2014-2019',
                'responsibilities': [
                    'モバイルアプリ開発',
                    'UI/UX設計',
                    '品質保証'
                ]
            }
        ],
        'skills': 'プログラミング言語: C++, Python, JavaScript, Swift | フレームワーク: Unity, Unreal Engine | クラウド: AWS, Azure',
        'contact': {
            'Portfolio': 'https://tanakataro.dev',
            'Twitter': '@tanaka_dev',
            'Facebook': 'https://facebook.com/tanaka.taro'
        }
    }
    
    return create_cv_pdf('imaginary_test_cvs/CV_Tanaka_Taro.pdf', content, 'JP')

def create_brazilian_cv():
    """Create Brazilian CV with challenging PII."""
    content = {
        'title': 'Currículo',
        'personal': {
            'Nome': 'Carlos Alberto Silva Santos',
            'Data de Nascimento': '25/07/1989',
            'Idade': '34 anos',
            'Nacionalidade': 'Brasileira',
            'CPF': '123.456.789-00',
            'RG': 'MG-12.345.678',
            'Endereço': 'Rua das Flores, 123, Apto 404, Belo Horizonte, MG 30140-071, Brasil',
            'Telefone': '+55 31 98765-4321',
            'Telefone Fixo': '+55 31 3456-7890',
            'Email': 'carlos.silva89@gmail.com',
            'LinkedIn': 'https://br.linkedin.com/in/carlosalbertosilva',
            'GitHub': 'https://github.com/carlossilva'
        },
        'education': [
            {
                'degree': 'Mestrado em Engenharia de Software',
                'years': '2014-2016',
                'institution': 'Universidade Federal de Minas Gerais',
                'details': 'CGPA: 9.2/10'
            },
            {
                'degree': 'Bacharelado em Ciência da Computação',
                'years': '2010-2014',
                'institution': 'Universidade Federal de Minas Gerais',
                'details': 'CGPA: 8.7/10'
            }
        ],
        'experience': [
            {
                'position': 'Arquiteto de Software Sênior',
                'company': 'Petrobras',
                'years': '2020-Atual',
                'responsibilities': [
                    'Desenvolvimento de sistemas de integração de dados',
                    'Arquitetura de nuvem',
                    'Liderança técnica'
                ]
            },
            {
                'position': 'Desenvolvedor Full Stack',
                'company': 'Magazine Luiza',
                'years': '2016-2020',
                'responsibilities': [
                    'Desenvolvimento de e-commerce',
                    'API RESTful',
                    'Banco de dados NoSQL'
                ]
            }
        ],
        'skills': 'Linguagens: Java, Python, JavaScript, TypeScript | Frameworks: Spring Boot, React, Angular | Cloud: AWS, Google Cloud',
        'contact': {
            'Portfolio': 'https://carlossilva.dev',
            'Twitter': '@carlos_tech_br',
            'Instagram': '@carlos.dev'
        }
    }
    
    return create_cv_pdf('imaginary_test_cvs/CV_Carlos_Silva.pdf', content, 'BR')

def create_arabic_cv():
    """Create Arabic CV with challenging PII."""
    content = {
        'title': 'سيرة ذاتية',
        'personal': {
            'Name': 'أحمد محمد علي (Ahmed Mohamed Ali)',
            'Date of Birth': '03/03/1991',
            'Age': '32 years',
            'Nationality': 'Egyptian',
            'National ID': '29003011234567',
            'Passport': 'A12345678',
            'Address': '123 Al-Ahram Street, Apt 5, Nasr City, Cairo 11511, Egypt',
            'Phone': '+20 2 2267-8910',
            'Mobile': '+20 10 1234-5678',
            'Email': 'ahmed.mohamed@siliconminds.com.eg',
            'LinkedIn': 'https://eg.linkedin.com/in/ahmedmohamed',
            'GitHub': 'https://github.com/ahmedmohamed91'
        },
        'education': [
            {
                'degree': 'Master of Computer Science',
                'years': '2016-2018',
                'institution': 'American University in Cairo',
                'details': 'GPA: 3.8/4.0'
            },
            {
                'degree': 'Bachelor of Computer Engineering',
                'years': '2013-2016',
                'institution': 'Cairo University',
                'details': 'GPA: 3.9/4.0'
            }
        ],
        'experience': [
            {
                'position': 'Senior Software Engineer',
                'company': 'SiliconMinds',
                'years': '2021-Present',
                'responsibilities': [
                    'AI/ML system development',
                    'Cloud architecture',
                    'Team leadership'
                ]
            },
            {
                'position': 'Full Stack Developer',
                'company': 'Vezeeta',
                'years': '2019-2021',
                'responsibilities': [
                    'Healthcare platform development',
                    'API development',
                    'Database optimization'
                ]
            }
        ],
        'skills': 'Languages: Python, JavaScript, Java, PHP | Frameworks: Django, Flask, React, Laravel | Cloud: AWS, Google Cloud, Azure',
        'contact': {
            'Portfolio': 'https://ahmedmohamed.dev',
            'Twitter': '@ahmed_tech',
            'Facebook': 'https://facebook.com/ahmed.mohamed.1991'
        }
    }
    
    return create_cv_pdf('imaginary_test_cvs/CV_Ahmed_Mohamed.pdf', content, 'EG')

def create_mexican_cv():
    """Create Mexican CV with challenging PII."""
    content = {
        'title': 'Curriculum Vitae',
        'personal': {
            'Name': 'José Luis García Hernández',
            'Fecha de Nacimiento': '12/06/1988',
            'Edad': '35 años',
            'Nacionalidad': 'Mexicana',
            'CURP': 'GAHJ880612HDFXXX09',
            'RFC': 'GAHJ880612XYZ',
            'Dirección': 'Calle Reforma 123, Depto 45, Colonia Juárez, Cuauhtémoc, 06600, Ciudad de México, CDMX',
            'Teléfono': '+52 55 1234-5678',
            'Celular': '+52 1 55 8765-4321',
            'Email': 'jose.garcia@tecmex.com.mx',
            'LinkedIn': 'https://mx.linkedin.com/in/joseluisgarcia',
            'GitHub': 'https://github.com/joseluisgarcia88'
        },
        'education': [
            {
                'degree': 'Maestría en Ciencias de la Computación',
                'years': '2014-2016',
                'institution': 'Universidad Nacional Autónoma de México',
                'details': 'Promedio: 9.5/10'
            },
            {
                'degree': 'Licenciatura en Ingeniería de Software',
                'years': '2010-2014',
                'institution': 'Instituto Tecnológico y de Estudios Superiores de Monterrey',
                'details': 'Promedio: 9.2/10'
            }
        ],
        'experience': [
            {
                'position': 'Arquitecto de Software Senior',
                'company': 'Tecmex',
                'years': '2020-Presente',
                'responsibilities': [
                    'Desarrollo de sistemas financieros',
                    'Arquitectura microservices',
                    'Mentoría de equipo'
                ]
            },
            {
                'position': 'Desarrollador Full Stack',
                'company': 'MercadoLibre',
                'years': '2016-2020',
                'responsibilities': [
                    'Plataforma e-commerce',
                    'API RESTful',
                    'Análisis de datos'
                ]
            }
        ],
        'skills': 'Lenguajes: Python, Java, JavaScript, C# | Frameworks: Django, Spring Boot, React, .NET | Cloud: AWS, Azure, Google Cloud',
        'contact': {
            'Portfolio': 'https://josegarcia.dev',
            'Twitter': '@jose_garcia_tech',
            'Instagram': '@jose.luis.dev'
        }
    }
    
    return create_cv_pdf('imaginary_test_cvs/CV_Jose_Garcia.pdf', content, 'MX')

if __name__ == '__main__':
    # Register custom fonts
    register_custom_fonts()
    
    # Create directory if it doesn't exist
    os.makedirs('imaginary_test_cvs', exist_ok=True)
    
    # Create PDF CVs
    print("Creating German CV...")
    create_german_cv()
    
    print("Creating Japanese CV...")
    create_japanese_cv()
    
    print("Creating Brazilian CV...")
    create_brazilian_cv()
    
    print("Creating Arabic CV...")
    create_arabic_cv()
    
    print("Creating Mexican CV...")
    create_mexican_cv()
    
    print("All PDF CVs created successfully!")
