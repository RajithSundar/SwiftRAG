<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <h3 align="center">SwiftVisa AI - Infosys Springboard Virtual Internship</h3>

  <p align="center">
    An AI-powered visa eligibility screening agent using Retrieval-Augmented Generation (RAG).
    <br />
    <a href="https://github.com/RajithSundar/SwiftRAG"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/RajithSundar/SwiftRAG/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/RajithSundar/SwiftRAG/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- ABOUT THE PROJECT -->
## About The Project

SwiftVisa AI is an intelligent visa consultation and eligibility screening tool. By leveraging Retrieval-Augmented Generation (RAG), the system ingests official US and UK immigration policy manuals to provide users with accurate, verifiable, and highly relevant visa guidance.

The application evaluates user profiles against complex immigration requirements, assesses risk factors (such as 214(b) rejections), and simulates an expert consultation experience.

### Built With

* [Streamlit](https://streamlit.io/)
* [LangChain](https://python.langchain.com/)
* [ChromaDB](https://www.trychroma.com/)
* [Groq](https://groq.com/)
* [Google Gemini AI](https://deepmind.google/technologies/gemini/)

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

* Python 3.9 or higher
* pip
  ```sh
  pip install --upgrade pip
  ```

### Installation

1. Get API Keys for Groq and Google Gemini.
2. Clone the repo
   ```sh
   git clone https://github.com/RajithSundar/SwiftRAG.git
   ```
3. Install Python packages
   ```sh
   pip install -r requirements.txt
   ```
4. Copy the example environment file and enter your API keys
   ```sh
   cp .env.example .env
   ```
5. Update `.env` with your actual API keys.

<!-- USAGE EXAMPLES -->
## Usage

To start the application locally, run the following command from the root directory:

```sh
streamlit run app.py
```

This will launch the Streamlit interface in your default web browser, where you can interact with the SwiftVisa AI consultant.

<!-- DEPLOYMENT -->
## Deployment

This repository comes pre-baked with an offline vector database (`chroma_db`) enabling seamless read-only deployment on cloud platforms like Render.

1. Connect the repository to your Render account.
2. Set the build command: `pip install -r requirements.txt`
3. Set the start command: `streamlit run app.py`
4. Add the environment variables from your `.env` file to the Render dashboard.

<!-- ROADMAP -->
## Roadmap

- [ ] Add support for additional countries (e.g., Canada, Australia)
- [ ] Migrate to a managed cloud vector database (e.g., Pinecone)
- [ ] Improve adversarial query handling
- [ ] Integrate multi-language support

See the [open issues](https://github.com/RajithSundar/SwiftRAG/issues) for a full list of proposed features (and known issues).

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<!-- CONTACT -->
## Contact

Rajith Sundar - [@RajithSundar](https://github.com/RajithSundar)

Project Link: [https://github.com/RajithSundar/SwiftRAG](https://github.com/RajithSundar/SwiftRAG)
