"""
Flaxem product catalog, taken from https://flaxem.com/our-products/.

Only descriptive facts live here. Operational settings (launch_url,
provisioning_mode, is_enabled) belong to the deployment and are managed in the
admin, so `seed_platform` never overwrites them on existing rows.

info_url values follow the site's navigation menu; the page's own "Read more"
links differ for Infor OS and Dynamics 365, so verify those two in the admin.
"""

BASE = "https://flaxem.com/our-products"

CATALOG = [
    {
        "slug": "dms",
        "name": "FSE DMS (Document Management System)",
        "description": "Central platform to capture, store and retrieve business documents.",
        "info_url": f"{BASE}/fse-dms-document-management-system/",
        "sort_order": 10,
    },
    {
        "slug": "infor-sunsystems-erp",
        "name": "Infor SunSystems ERP",
        "description": "Financial management with real-time insight and multi-currency support.",
        "info_url": f"{BASE}/infor-sunsystems-erp/",
        "sort_order": 20,
    },
    {
        "slug": "work-pro-hrms",
        "name": "WORK PRO HRMS (HR & Payroll)",
        "description": "Integrated human resource and payroll management.",
        "info_url": f"{BASE}/work-pro-hrms-hr-payroll/",
        "sort_order": 30,
    },
    {
        "slug": "e-procurement",
        "name": "E-Procurement System (FSE ProcureNet)",
        "description": "End-to-end digital procurement, from planning through the full lifecycle.",
        "info_url": f"{BASE}/e-procurement-system/",
        "sort_order": 40,
    },
    {
        "slug": "power-bi",
        "name": "Power BI Reporting Tool",
        "description": "Interactive dashboards and business intelligence reporting.",
        "info_url": f"{BASE}/power-bi-reporting-tool/",
        "sort_order": 50,
    },
    {
        "slug": "infor-os",
        "name": "Infor OS",
        "description": "Cloud operating platform that connects people, processes and applications.",
        "info_url": f"{BASE}/infor-os/",
        "sort_order": 60,
    },
    {
        "slug": "dynamics-365-erp",
        "name": "Microsoft Dynamics 365 – ERP",
        "description": "ERP and CRM suite covering finance, operations, sales and customer service.",
        "info_url": f"{BASE}/microsoft-dynamics-365-erp/",
        "sort_order": 70,
    },
    {
        "slug": "azure-hosting",
        "name": "Microsoft Azure Cloud Hosting",
        "description": "Scalable, secure cloud hosting for applications, data and infrastructure.",
        "info_url": f"{BASE}/microsoft-azure-cloud-hosting/",
        "sort_order": 80,
    },
    {
        "slug": "e-payment",
        "name": "E-Payment System",
        "description": "Electronic payments that speed up cash flow and reduce manual errors.",
        "info_url": f"{BASE}/e-payment-system/",
        "sort_order": 90,
    },
    {
        "slug": "efris",
        "name": "Electronic Fiscal Receipting and Invoicing System (EFRIS)",
        "description": "EFRIS integration that automates invoicing and tax compliance.",
        "info_url": f"{BASE}/electronic-fiscal-receipting-and-invoicing-system-efris/",
        "sort_order": 100,
    },
]
