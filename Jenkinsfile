
pipeline{
    choice(
        choices: ['JOBTEMPLATES', 'URLS'], 
        name: 'START_METHOD',
        description:'Optionally deploy the UI to the hotfix or updates location'
    )
    stages{
        stage('Run Job Templates'){
            environment {
                API_KEY = credentials('devops-api-key')
            }
            when {
                expression {
                    return params.START_METHOD=='JOBTEMPLATES-CURRENT'
                }
            }
            steps{
                script{
                    pwsh """
                        \$ErrorActionPreference = "Stop"
                        ./run-job-templates.ps1 -apiKey ${API_KEY}
                    """
                }
            }
        }
        stage('Run URLs'){
            environment {
                API_KEY = credentials('devops-api-key')
            }
            when {
                expression {
                    return params.START_METHOD=='URLS'
                }
            }
            steps{
                script{
                    pwsh """
                        \$ErrorActionPreference = "Stop"
                        ./run-urls.ps1 -apiKey ${API_KEY}
                    """
                }
            }
        }
    }
}