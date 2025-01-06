
pipeline{
    parameters{
        choice(
            choices: ['URLS', 'JOBTEMPLATES'], 
            name: 'START_METHOD',
            description:'Optionally deploy the UI to the hotfix or updates location'
        )
        string(
            defaultValue: 'https://localhost:9000', 
            name: 'MASTER_ADDRESS', 
            trim: true
        )
    }
    agent any
    environment {
        DEVOPS_API_KEY = credentials('devops-api-key')
    }
    stages{
        stage('Run Job Templates'){
            when {
                expression {
                    return params.START_METHOD=='JOBTEMPLATES'
                }
            }
            steps{
                script{
                    pwsh """
                        \$ErrorActionPreference = "Stop"
                        ./run-job-templates.ps1 ${params.MASTER_ADDRESS}
                    """
                }
            }
        }
        stage('Run URLs'){
            when {
                expression {
                    return params.START_METHOD=='URLS'
                }
            }
            steps{
                script{
                    pwsh """
                        \$ErrorActionPreference = "Stop"
                        ./run-urls.ps1 ${params.MASTER_ADDRESS}
                    """
                }
            }
        }
    }
}